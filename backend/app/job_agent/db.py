import psycopg2
import json
import os

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        return json.load(f)

def get_db_connection():
    config = load_config()
    pg = config.get("postgres", {})
    return psycopg2.connect(
        host=pg.get("host", "localhost"),
        port=pg.get("port", 5432),
        database=pg.get("database", "postgres"),
        user=pg.get("user", "postgres"),
        password=pg.get("password", ""),
        options="-c search_path=vidyamarg"
    )

def init_db():
    config = load_config()
    table_name = config.get("postgres", {}).get("table_name", "jobs")
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    
    # 1. telegram_channels
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telegram_channels (
        channel_id VARCHAR(100) PRIMARY KEY,
        channel_name VARCHAR(255),
        last_processed_message_id INTEGER DEFAULT 0,
        last_sync_time TIMESTAMPTZ,
        status VARCHAR(50),
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
    );
    """)
    
    # 2. telegram_messages
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS telegram_messages (
        id SERIAL PRIMARY KEY,
        channel_id VARCHAR(100) REFERENCES telegram_channels(channel_id),
        telegram_message_id INTEGER,
        message_date TIMESTAMPTZ,
        message_text TEXT,
        media_count INTEGER DEFAULT 0,
        processed BOOLEAN DEFAULT FALSE,
        processing_status VARCHAR(50), -- 'DOWNLOADED', 'OCR_SUCCESS', 'OCR_FAILED', 'PARSED', 'INVALID', 'DUPLICATE', 'SAVED'
        retry_count INTEGER DEFAULT 0,
        created_at TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (channel_id, telegram_message_id)
    );
    """)
    
    # Alter telegram_messages table to add retry_count column if it doesn't exist
    cursor.execute("ALTER TABLE telegram_messages ADD COLUMN IF NOT EXISTS retry_count INTEGER DEFAULT 0;")
    
    # ── Migration: ensure job_sources table exists (created by SQLAlchemy models on first run)
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS job_sources (
        id SERIAL PRIMARY KEY,
        name VARCHAR(100) UNIQUE NOT NULL,
        display_name VARCHAR(100) NOT NULL,
        source_type VARCHAR(50) NOT NULL,
        is_active BOOLEAN DEFAULT TRUE,
        priority INTEGER DEFAULT 5
    );
    """)

    # ── Migration: seed Telegram source row ──────────────────────────────────
    cursor.execute("""
        INSERT INTO job_sources (name, display_name, source_type, is_active, priority)
        VALUES ('telegram_agent', 'Telegram Job Agent', 'scraper', TRUE, 3)
        ON CONFLICT (name) DO NOTHING;
    """)

    # ── Migration: add meta column to jobs if not present ────────────────────
    cursor.execute("""
        ALTER TABLE jobs ADD COLUMN IF NOT EXISTS meta JSONB DEFAULT '{}'::jsonb;
    """)

    # ── Migration: add unique constraint for ON CONFLICT (external_id, source_id)
    cursor.execute("""
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint
                WHERE conname = 'uq_job_external_source'
            ) THEN
                ALTER TABLE jobs
                ADD CONSTRAINT uq_job_external_source
                UNIQUE (external_id, source_id);
            END IF;
        END $$;
    """)

    # 4. app_leader
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS app_leader (
        instance_id VARCHAR(100) PRIMARY KEY,
        last_seen TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP,
        status VARCHAR(50)
    );
    """)
    
    cursor.close()
    conn.close()

def get_channel_state(channel_id: str) -> int:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT last_processed_message_id FROM telegram_channels WHERE channel_id = %s;", (channel_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else 0

def update_channel_state(channel_id: str, channel_name: str, last_msg_id: int, status: str):
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO telegram_channels (channel_id, channel_name, last_processed_message_id, last_sync_time, status)
        VALUES (%s, %s, %s, CURRENT_TIMESTAMP, %s)
        ON CONFLICT (channel_id) DO UPDATE SET
            last_processed_message_id = EXCLUDED.last_processed_message_id,
            last_sync_time = CURRENT_TIMESTAMP,
            status = EXCLUDED.status,
            updated_at = CURRENT_TIMESTAMP;
    """, (channel_id, channel_name, last_msg_id, status))
    cursor.close()
    conn.close()

def insert_raw_message(channel_id: str, msg_id: int, date_obj, text: str, media_count: int):
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        cursor.execute("""
            INSERT INTO telegram_messages (channel_id, telegram_message_id, message_date, message_text, media_count, processed, processing_status, retry_count)
            VALUES (%s, %s, %s, %s, %s, FALSE, 'PENDING', 0)
            ON CONFLICT (channel_id, telegram_message_id) DO NOTHING;
        """, (channel_id, msg_id, date_obj, text, media_count))
    except Exception as e:
        print(f"[WARNING] Failed to insert raw message {msg_id}: {e}")
    finally:
        cursor.close()
        conn.close()

def mark_message_processed(channel_id: str, msg_id: int, status: str):
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    processed = (status in ("SAVED", "DUPLICATE", "INVALID"))
    cursor.execute("""
        UPDATE telegram_messages 
        SET processed = %s, processing_status = %s
        WHERE channel_id = %s AND telegram_message_id = %s;
    """, (processed, status, channel_id, msg_id))
    cursor.close()
    conn.close()

def increment_retry_count(channel_id: str, msg_id: int, status: str):
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE telegram_messages 
        SET retry_count = retry_count + 1, processing_status = %s, processed = FALSE
        WHERE channel_id = %s AND telegram_message_id = %s;
    """, (status, channel_id, msg_id))
    cursor.close()
    conn.close()

def get_ocr_failed_messages():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT channel_id, telegram_message_id, message_date, message_text, media_count, retry_count 
        FROM telegram_messages 
        WHERE processing_status = 'OCR_FAILED' AND retry_count < 3 AND processed = FALSE;
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows

def is_url_already_processed(url: str) -> bool:
    """Checks if a URL has already been scraped and saved in the main jobs table."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1 FROM jobs WHERE apply_url = %s LIMIT 1;", (url,))
    exists = cursor.fetchone() is not None
    cursor.close()
    conn.close()
    return exists

def get_existing_job_by_url(url: str) -> dict:
    """Fetches an existing job record matching the given URL to reuse it."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT title, company_name, location, salary_raw, apply_url
        FROM jobs
        WHERE apply_url = %s
        LIMIT 1;
    """, (url,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    if row:
        return {
            "title":      row[0],
            "company":    row[1],
            "location":   row[2],
            "salary":     row[3],
            "apply_link": row[4],
        }
    return None

def upsert_job(job_dict: dict, job_hash: str) -> bool:
    config = load_config()
    table_name = config.get("postgres", {}).get("table_name", "jobs")
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    
    insert_query = f"""
    INSERT INTO {table_name} (
        channel, message_id, date, title, company, location,
        experience, skills, salary, apply_link, original_link,
        email, message_link, raw_text, job_hash
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (job_hash) DO UPDATE SET
        channel = EXCLUDED.channel,
        message_id = EXCLUDED.message_id,
        date = EXCLUDED.date,
        title = EXCLUDED.title,
        company = EXCLUDED.company,
        location = EXCLUDED.location,
        experience = EXCLUDED.experience,
        skills = EXCLUDED.skills,
        salary = EXCLUDED.salary,
        apply_link = EXCLUDED.apply_link,
        original_link = EXCLUDED.original_link,
        email = EXCLUDED.email,
        message_link = EXCLUDED.message_link,
        raw_text = EXCLUDED.raw_text;
    """
    
    # Check if job_hash already exists in the table.
    cursor.execute(f"SELECT 1 FROM {table_name} WHERE job_hash = %s LIMIT 1;", (job_hash,))
    if cursor.fetchone():
        cursor.close()
        conn.close()
        return False
        
    val_tuple = (
        job_dict.get("channel"),
        job_dict.get("message_id"),
        job_dict.get("date"),
        job_dict.get("title"),
        job_dict.get("company"),
        job_dict.get("location"),
        job_dict.get("experience"),
        job_dict.get("skills"),
        job_dict.get("salary"),
        job_dict.get("apply_link"),
        job_dict.get("original_link"),
        job_dict.get("email"),
        job_dict.get("message_link"),
        job_dict.get("raw_text"),
        job_hash
    )
    cursor.execute(insert_query, val_tuple)
    cursor.close()
    conn.close()
    return True


def upsert_jobs_batch(job_records: list) -> int:
    """
    Saves a list of Telegram-scraped job records directly into the main VidyaMarg AI
    'jobs' table (matching the SQLAlchemy Job model schema in job_models.py).

    Uses ON CONFLICT (external_id) DO NOTHING for deduplication.
    Returns the number of successfully inserted rows.
    """
    if not job_records:
        return 0

    import hashlib
    import json as _json
    from datetime import datetime, timezone

    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()

    # Ensure a dedicated source row exists for Telegram jobs
    cursor.execute("""
        INSERT INTO job_sources (name, display_name, source_type, is_active, priority)
        VALUES ('telegram_agent', 'Telegram Job Agent', 'scraper', TRUE, 3)
        ON CONFLICT (name) DO NOTHING;
    """)
    cursor.execute("SELECT id FROM job_sources WHERE name = 'telegram_agent';")
    row = cursor.fetchone()
    source_id = row[0] if row else None

    insert_query = """
    INSERT INTO jobs (
        external_id,
        source_id,
        title,
        title_normalized,
        company_name,
        description,
        apply_url,
        job_url,
        location,
        is_remote,
        required_skills,
        preferred_skills,
        salary_raw,
        work_mode,
        lifecycle_status,
        is_active,
        is_verified,
        trust_score,
        quality_score,
        freshness_score,
        spam_score,
        posted_at,
        discovered_at,
        created_at,
        updated_at,
        meta
    ) VALUES (
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
        %s, %s, %s, %s, %s, %s
    )
    ON CONFLICT (external_id, source_id) DO NOTHING;
    """

    val_tuples = []
    now = datetime.now(timezone.utc)

    for job_dict in job_records:
        # Build a stable external_id from the resolved apply URL
        apply_url = job_dict.get("original_link") or job_dict.get("apply_link") or ""
        if apply_url in ("unresolved", "N/A", ""):
            apply_url = job_dict.get("apply_link") or job_dict.get("email") or "no_link"
        norm_url = (apply_url or "").strip().lower()
        external_id = hashlib.sha256(norm_url.encode("utf-8")).hexdigest()

        title = (job_dict.get("title") or "N/A").strip()[:499]
        company_name = (job_dict.get("company") or "Unknown").strip()[:254]
        location_raw = (job_dict.get("location") or "").strip()[:499]
        description = job_dict.get("raw_text") or ""
        salary_raw = (job_dict.get("salary") or "").strip()[:254]
        skills_raw = job_dict.get("skills") or ""
        required_skills = [s.strip() for s in skills_raw.split(",") if s.strip()] if skills_raw else []

        is_remote = any(w in location_raw.lower() for w in ["remote", "wfh", "work from home"])
        work_mode = "remote" if is_remote else "onsite"

        # Parse posted_at from Telegram message date
        posted_at = None
        date_str = job_dict.get("date")
        if date_str:
            try:
                posted_at = datetime.fromisoformat(date_str)
            except Exception:
                posted_at = now

        # Telegram channel and message metadata stored in meta JSON
        meta = {
            "telegram_channel": job_dict.get("channel"),
            "telegram_message_id": job_dict.get("message_id"),
            "message_link": job_dict.get("message_link"),
            "original_link": job_dict.get("original_link"),
            "email": job_dict.get("email"),
            "experience": job_dict.get("experience"),
            "source": "telegram_agent",
        }

        val_tuple = (
            external_id,                        # external_id
            source_id,                          # source_id
            title,                              # title
            title.lower(),                      # title_normalized
            company_name,                       # company_name
            description[:5000],                 # description
            apply_url[:999],                    # apply_url
            job_dict.get("message_link") or "", # job_url
            location_raw,                       # location
            is_remote,                          # is_remote
            _json.dumps(required_skills),       # required_skills (JSON)
            _json.dumps([]),                    # preferred_skills (JSON)
            salary_raw,                         # salary_raw
            work_mode,                          # work_mode
            "persisted",                        # lifecycle_status
            True,                               # is_active
            False,                              # is_verified
            0.6,                                # trust_score
            0.5,                                # quality_score
            1.0,                                # freshness_score
            0.1,                                # spam_score
            posted_at or now,                   # posted_at
            now,                                # discovered_at
            now,                                # created_at
            now,                                # updated_at
            _json.dumps(meta),                  # meta
        )
        val_tuples.append(val_tuple)

    inserted_count = 0
    try:
        for val_tuple in val_tuples:
            try:
                cursor.execute(insert_query, val_tuple)
                inserted_count += 1
            except Exception as row_err:
                print(f"  [WARN] Skipped job row: {row_err}")
    finally:
        cursor.close()
        conn.close()

    return inserted_count


def expire_old_telegram_jobs(days: int = 7) -> int:
    """
    Marks Telegram-sourced jobs older than `days` days as inactive (is_active = FALSE)
    in the main VidyaMarg AI jobs table.

    Called by the APScheduler every night. Returns the count of expired rows.
    """
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    try:
        cursor.execute("""
            UPDATE jobs
            SET
                is_active      = FALSE,
                lifecycle_status = 'expired',
                updated_at     = CURRENT_TIMESTAMP
            WHERE
                source_id = (SELECT id FROM job_sources WHERE name = 'telegram_agent')
                AND is_active = TRUE
                AND posted_at < (CURRENT_TIMESTAMP - INTERVAL '%s days');
        """, (days,))
        expired = cursor.rowcount
        print(f"[expire_old_telegram_jobs] Expired {expired} job(s) older than {days} days.")
        return expired
    except Exception as e:
        print(f"[expire_old_telegram_jobs] ERROR: {e}")
        return 0
    finally:
        cursor.close()
        conn.close()


def register_instance(instance_id: str):
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("""
        INSERT INTO app_leader (instance_id, last_seen, status)
        VALUES (%s, CURRENT_TIMESTAMP, 'active')
        ON CONFLICT (instance_id) DO UPDATE SET
            last_seen = CURRENT_TIMESTAMP,
            status = 'active';
    """, (instance_id,))
    cursor.close()
    conn.close()


def get_active_instances() -> list:
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("""
        SELECT instance_id, status FROM app_leader
        WHERE last_seen > CURRENT_TIMESTAMP - INTERVAL '15 seconds';
    """)
    rows = cursor.fetchall()
    cursor.close()
    conn.close()
    return rows


def request_takeover(target_instance_id: str):
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("UPDATE app_leader SET status = 'stopping' WHERE instance_id = %s;", (target_instance_id,))
    cursor.close()
    conn.close()


def heartbeat_instance(instance_id: str) -> str:
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("""
        UPDATE app_leader SET last_seen = CURRENT_TIMESTAMP
        WHERE instance_id = %s
        RETURNING status;
    """, (instance_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None


def unregister_instance(instance_id: str):
    conn = get_db_connection()
    conn.autocommit = True
    cursor = conn.cursor()
    cursor.execute("DELETE FROM app_leader WHERE instance_id = %s;", (instance_id,))
    cursor.close()
    conn.close()
