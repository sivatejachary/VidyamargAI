import argparse
import asyncio
import concurrent.futures
import csv
import json
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser

# Force UTF-8 output so emoji/Unicode in job titles never crash on Windows cp1252
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


try:
    from telethon import TelegramClient, events
    from telethon.errors import SessionPasswordNeededError
except ImportError:
    print("Telethon is not installed. Run: pip install -r requirements.txt --break-system-packages")
    sys.exit(1)

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")
CHANNELS_PATH = os.path.join(os.path.dirname(__file__), "channel.txt")
SESSION_NAME = os.path.join(os.path.dirname(__file__), "job_agent_session")

DEFAULT_KEYWORDS = [
    "hiring", "job opening", "job opportunity", "we're looking for",
    "we are looking for", "apply now", "vacancy", "vacancies",
    "job alert", "job vacancy", "job description", "jd:", "urgent hiring",
    "walk-in", "walkin interview", "career opportunity", "role:", "position:",
]

# Regex patterns used to pull structured fields out of free-text job posts.
FIELD_PATTERNS = {
    "title": r"(?:job\s*title|role|position|designation|post\s*name|job\s*role)\s*[:\-]\s*(.+)",
    "company": r"(?:company\s*name|company|organi[sz]ation|employer)\s*[:\-]\s*(.+)",
    "location": r"(?:location|city|based\s*in|work\s*location|job\s*location)\s*[:\-]\s*(.+)",
    "experience": r"(?:experience|exp|eligibility|batch(?:es)?|qualification)\s*[:\-]\s*(.+)",
    "skills": r"(?:skills|key\s*skills|requirements|knowledge|tech\s*stack|stack|skills\s*required)\s*[:\-]\s*(.+)",
    "salary": r"(?:salary|ctc|package|package\s*expected)\s*[:\-]\s*(.+)",
    "apply_link": r"(https?://\S+)",
    "email": r"([\w\.\-]+@[\w\.\-]+\.\w+)",
}

# ── URL Classification ─────────────────────────────────────────────────────────
# Pure ATS platforms — any URL on these domains is a direct apply page
ATS_DOMAINS = [
    "greenhouse.io", "lever.co", "workday.com", "myworkdayjobs.com",
    "taleo.net", "icims.com", "smartrecruiters.com", "jobvite.com",
    "successfactors.com", "superset.ai", "wellfound.com", "unstop.com",
    "peoplestrongjobs.com", "oraclecloud.com", "hirehive.com",
    "jobs.lever.co", "apply.workable.com", "jobs.ashbyhq.com",
    "breezy.hr", "recruitcrm.io", "hire.withgoogle.com", "amazon.jobs",
    "docs.google.com", "forms.gle", "forms.google.com",
    "youtube.com", "youtu.be",
]

# Aggregator blog / job-listing sites — real link is buried inside the page
AGGREGATOR_DOMAINS = [
    "job4freshers.co.in", "freshershunt.in", "internshipss.com",
    "offcampusjobdrives.com", "kickcharm.com", "hiringdaily.in",
    "fresherjobsupdates.in", "studentpod.co",
    "sarkariresult.com", "ambitionbox.com",
]

# URL shorteners / one-hop redirects
SHORTENER_DOMAINS = [
    "bit.ly", "tinyurl.com", "pdlink.in", "wa.link", "lnkd.in",
    "yt.openinapp.co", "openinapp.co", "rebrand.ly", "shorturl.at",
    "cutt.ly", "t.co", "tiny.cc", "sendibt3.com",
]

# Social / noise — skip entirely when hunting for real apply links
SKIP_DOMAINS = {
    "t.me", "telegram.me", "telegram.dog", "whatsapp.com", "facebook.com",
    "instagram.com", "twitter.com", "x.com", "play.google.com",
    "youtube.com", "youtu.be", "openinapp.co", "yt.openinapp.co",
}

# Patterns that indicate a resolved link is NOT a real apply page
# (YouTube subscription, Telegram channel, WhatsApp home, etc.)
BAD_RESOLVED_PATTERNS = [
    "youtube.com",
    "youtu.be",
    "?sub_confirmation=",
    "telegram.dog/",
    "t.me/",
    "whatsapp.com",
    "linkedin.com/legal/",
    "placementdrive.in/category",
    "openinapp.co",
]


def is_valid_original_link(url: str) -> bool:
    """Return False if the resolved URL is clearly not a real job apply page."""
    if not url or url == "unresolved":
        return False
    for pattern in BAD_RESOLVED_PATTERNS:
        if pattern in url:
            return False
    return True

# Subdomain prefixes that mark an official company career page
# e.g. careers.capgemini.com  apply.cognizant.com  jobs.deloitte.com
CAREER_SUBDOMAIN_PREFIXES = (
    "careers.", "career.", "jobs.", "apply.", "talent.", "hiring.", "recruit.",
)


def classify_url(url: str) -> str:
    """Return 'OFFICIAL', 'AGGREGATOR', 'SHORTENER', 'SKIP', or 'OTHER'."""
    if not url or not url.startswith("http"):
        return "OTHER"
    from urllib.parse import urlparse
    try:
        host = urlparse(url).netloc.lower().lstrip("www.")
        path = urlparse(url).path.lower()
    except Exception:
        return "OTHER"
    # Social / noise
    for d in SKIP_DOMAINS:
        if host == d or host.endswith("." + d):
            return "SKIP"
    # Shorteners
    for d in SHORTENER_DOMAINS:
        if host == d or host.endswith("." + d):
            return "SHORTENER"
    for d in AGGREGATOR_DOMAINS:
        if host == d or host.endswith("." + d):
            return "AGGREGATOR"
            
    # ATS Platforms (OFFICIAL)
    for d in ATS_DOMAINS:
        if host == d or host.endswith("." + d):
            return "OFFICIAL"
            
    # Career Subdomains (OFFICIAL)
    if any(host.startswith(prefix) for prefix in CAREER_SUBDOMAIN_PREFIXES):
        return "OFFICIAL"
        
    return "OTHER"


def save_records_to_postgres(records: list):
    """
    Saves a list of job records to the PostgreSQL database if enabled in config.json.
    Performs an INSERT ... ON CONFLICT (channel, message_id) DO UPDATE (upsert).
    Also performs job-level deduplication across channels using a stable SHA-256 hash.
    """
    config = load_config()
    pg_config = config.get("postgres", {})
    if not pg_config or not pg_config.get("enabled", False):
        return

    import psycopg2
    import hashlib

    def generate_job_hash(title: str, company: str, location: str, apply_link: str) -> str:
        norm_url = (apply_link or "").strip().lower()
        return hashlib.sha256(norm_url.encode("utf-8")).hexdigest()

    host = pg_config.get("host", "localhost")
    port = pg_config.get("port", 5432)
    database = pg_config.get("database", "postgres")
    user = pg_config.get("user", "postgres")
    password = pg_config.get("password", "")
    table_name = pg_config.get("table_name", "jobs")

    print(f"Connecting to PostgreSQL database '{database}' on {host}:{port}...")
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        conn.autocommit = True
        cursor = conn.cursor()
    except Exception as e:
        print(f"[ERROR] Failed to connect to PostgreSQL: {e}")
        return

    # 1. Create table if not exists with job_hash column
    create_query = f"""
    CREATE TABLE IF NOT EXISTS {table_name} (
        channel VARCHAR(100),
        message_id INTEGER,
        date TIMESTAMPTZ,
        title TEXT,
        company TEXT,
        location TEXT,
        experience TEXT,
        skills TEXT,
        salary TEXT,
        apply_link TEXT,
        original_link TEXT,
        email TEXT,
        message_link TEXT,
        raw_text TEXT,
        job_hash VARCHAR(64) UNIQUE,
        PRIMARY KEY (channel, message_id)
    );
    """
    try:
        cursor.execute(create_query)
        # Ensure job_hash exists on an existing table from previous runs
        cursor.execute(f"ALTER TABLE {table_name} ADD COLUMN IF NOT EXISTS job_hash VARCHAR(64) UNIQUE;")
    except Exception as e:
        print(f"[ERROR] Failed to create table '{table_name}': {e}")
        conn.close()
        return

    # Load existing job hashes to check for duplicates
    existing_hashes = set()
    try:
        cursor.execute(f"SELECT job_hash FROM {table_name} WHERE job_hash IS NOT NULL;")
        for row in cursor.fetchall():
            existing_hashes.add(row[0])
    except Exception as e:
        print(f"[WARNING] Failed to load existing job hashes: {e}")

    # 2. Perform upsert
    insert_query = f"""
    INSERT INTO {table_name} (
        channel, message_id, date, title, company, location,
        experience, skills, salary, apply_link, original_link,
        email, message_link, raw_text, job_hash
    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
    ON CONFLICT (channel, message_id) DO UPDATE SET
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
        raw_text = EXCLUDED.raw_text,
        job_hash = EXCLUDED.job_hash;
    """

    success_count = 0
    duplicate_skipped_count = 0
    for r in records:
        title = r.get("title")
        company = r.get("company")
        location = r.get("location")
        apply_link = r.get("apply_link") or r.get("original_link")
        
        j_hash = generate_job_hash(title, company, location, apply_link)
        
        # Enforce cross-channel duplicate check: skip if hash already exists in DB
        if j_hash in existing_hashes:
            print(f"  [DUP HASH] Skipped duplicate job across channels: '{title}' at '{company}' (hash: {j_hash})")
            duplicate_skipped_count += 1
            continue
            
        existing_hashes.add(j_hash)

        date_str = r.get("date")
        date_obj = None
        if date_str:
            try:
                date_obj = datetime.fromisoformat(date_str)
            except ValueError:
                pass

        val_tuple = (
            r.get("channel"),
            r.get("message_id"),
            date_obj,
            title,
            company,
            location,
            r.get("experience"),
            r.get("skills"),
            r.get("salary"),
            r.get("apply_link"),
            r.get("original_link"),
            r.get("email"),
            r.get("message_link"),
            r.get("raw_text"),
            j_hash
        )

        try:
            cursor.execute(insert_query, val_tuple)
            success_count += 1
        except Exception as e:
            print(f"  [ERROR] Failed to insert job (ID: {r.get('message_id')}): {e}")

    cursor.close()
    conn.close()
    print(f"Successfully upserted {success_count} job record(s) to PostgreSQL. Skipped {duplicate_skipped_count} duplicates.")


def load_recent_records_from_postgres(days: int) -> list:
    """
    Fetch all jobs from the PostgreSQL database from the last N days to use for deduplication.
    """
    config = load_config()
    pg_config = config.get("postgres", {})
    if not pg_config or not pg_config.get("enabled", False):
        return []

    import psycopg2

    host = pg_config.get("host", "localhost")
    port = pg_config.get("port", 5432)
    database = pg_config.get("database", "postgres")
    user = pg_config.get("user", "postgres")
    password = pg_config.get("password", "")
    table_name = pg_config.get("table_name", "jobs")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)
    
    records = []
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        
        # Create table if not exists first
        cursor.execute(f"""
        CREATE TABLE IF NOT EXISTS {table_name} (
            channel VARCHAR(100),
            message_id INTEGER,
            date TIMESTAMPTZ,
            title TEXT,
            company TEXT,
            location TEXT,
            experience TEXT,
            skills TEXT,
            salary TEXT,
            apply_link TEXT,
            original_link TEXT,
            email TEXT,
            message_link TEXT,
            raw_text TEXT,
            PRIMARY KEY (channel, message_id)
        );
        """)
        
        query = f"""
        SELECT channel, message_id, date, title, company, location,
               experience, skills, salary, apply_link, original_link,
               email, message_link, raw_text
        FROM {table_name}
        WHERE date >= %s;
        """
        cursor.execute(query, (cutoff_date,))
        rows = cursor.fetchall()
        
        columns = [
            "channel", "message_id", "date", "title", "company", "location",
            "experience", "skills", "salary", "apply_link", "original_link",
            "email", "message_link", "raw_text"
        ]
        
        for r in rows:
            record = {}
            for col, val in zip(columns, r):
                if col == "date" and val:
                    record[col] = val.isoformat()
                else:
                    record[col] = val if val is not None else "N/A"
            records.append(record)
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WARNING] Failed to load recent jobs from PostgreSQL: {e}")
        
    return records


def load_unresolved_from_postgres() -> list:
    """
    Fetch all jobs from the PostgreSQL database where the original_link is
    missing or unresolved, and apply_link is present.
    """
    config = load_config()
    pg_config = config.get("postgres", {})
    if not pg_config or not pg_config.get("enabled", False):
        return []

    import psycopg2

    host = pg_config.get("host", "localhost")
    port = pg_config.get("port", 5432)
    database = pg_config.get("database", "postgres")
    user = pg_config.get("user", "postgres")
    password = pg_config.get("password", "")
    table_name = pg_config.get("table_name", "jobs")

    records = []
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        query = f"""
        SELECT channel, message_id, date, title, company, location,
               experience, skills, salary, apply_link, original_link,
               email, message_link, raw_text
        FROM {table_name}
        WHERE original_link IS NULL OR original_link = 'unresolved' OR original_link = '';
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        columns = [
            "channel", "message_id", "date", "title", "company", "location",
            "experience", "skills", "salary", "apply_link", "original_link",
            "email", "message_link", "raw_text"
        ]
        
        for r in rows:
            record = {}
            for col, val in zip(columns, r):
                if col == "date" and val:
                    record[col] = val.isoformat()
                else:
                    record[col] = val if val is not None else "N/A"
            records.append(record)
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to load unresolved jobs from PostgreSQL: {e}")
        
    return records


def load_all_jobs_from_postgres() -> list:
    """
    Fetch all jobs from the PostgreSQL database.
    """
    config = load_config()
    pg_config = config.get("postgres", {})
    if not pg_config or not pg_config.get("enabled", False):
        return []

    import psycopg2

    host = pg_config.get("host", "localhost")
    port = pg_config.get("port", 5432)
    database = pg_config.get("database", "postgres")
    user = pg_config.get("user", "postgres")
    password = pg_config.get("password", "")
    table_name = pg_config.get("table_name", "jobs")

    records = []
    try:
        conn = psycopg2.connect(
            host=host,
            port=port,
            database=database,
            user=user,
            password=password
        )
        cursor = conn.cursor()
        query = f"""
        SELECT channel, message_id, date, title, company, location,
               experience, skills, salary, apply_link, original_link,
               email, message_link, raw_text
        FROM {table_name};
        """
        cursor.execute(query)
        rows = cursor.fetchall()
        
        columns = [
            "channel", "message_id", "date", "title", "company", "location",
            "experience", "skills", "salary", "apply_link", "original_link",
            "email", "message_link", "raw_text"
        ]
        
        for r in rows:
            record = {}
            for col, val in zip(columns, r):
                if col == "date" and val:
                    record[col] = val.isoformat()
                else:
                    record[col] = val if val is not None else "N/A"
            records.append(record)
            
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[ERROR] Failed to load all jobs from PostgreSQL: {e}")
        
    return records




def load_channels_from_file() -> list:
    """
    Reads channel names/links from channel.txt, one per line.
    Blank lines and lines starting with # (comments) are ignored.
    Accepts usernames (with or without @), full t.me links, or numeric IDs.
    """
    if not os.path.exists(CHANNELS_PATH):
        with open(CHANNELS_PATH, "w") as f:
            f.write(
                "# Add one Telegram channel per line.\n"
                "# Accepts: username, @username, https://t.me/username, or a numeric channel ID.\n"
                "# Lines starting with # are ignored.\n"
                "examplejobschannel\n"
            )
        print(f"Created a starter {CHANNELS_PATH}. Add your channel usernames/links to it (one per line), then re-run.")
        sys.exit(0)

    channels = []
    with open(CHANNELS_PATH) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            channels.append(line)

    if not channels:
        print(f"{CHANNELS_PATH} has no channels listed. Add at least one channel (one per line) and re-run.")
        sys.exit(0)

    return channels


def load_config():
    if not os.path.exists(CONFIG_PATH):
        default_config = {
            "api_id": "32177444",
            "api_hash": "6d2b79f628a6ab09b993fb59c1db1504",
            "phone": "+919866862016",
            "keywords": DEFAULT_KEYWORDS,
            "history_limit": 300,
        }
        with open(CONFIG_PATH, "w") as f:
            json.dump(default_config, f, indent=2)
        print(f"Created a starter config at {CONFIG_PATH}. Edit it with your API credentials, then re-run.")
        sys.exit(0)

    with open(CONFIG_PATH) as f:
        config = json.load(f)

    if config.get("api_id") == "PUT_YOUR_API_ID_HERE" or not config.get("api_id"):
        print(f"Please fill in your Telegram api_id / api_hash / phone in {CONFIG_PATH} first.")
        print("Get them for free at https://my.telegram.org -> API development tools")
        sys.exit(0)

    config["channels"] = load_channels_from_file()
    return config


def looks_like_job_post(text: str, keywords) -> bool:
    if not text:
        return False
    lowered = text.lower()
    return any(kw.lower() in lowered for kw in keywords)


def extract_fields(text: str) -> dict:
    fields = {}

    # ── Collect ALL URLs from the message ─────────────────────────────────────
    all_urls = re.findall(r"(https?://[^\s)>\]'\"]+)", text, re.IGNORECASE)
    # Clean trailing punctuation that may have been captured
    all_urls = [u.rstrip(".,;:!?'\"") for u in all_urls]

    # Classify every URL found in the message
    official_urls    = [u for u in all_urls if classify_url(u) == "OFFICIAL"]
    aggregator_urls  = [u for u in all_urls if classify_url(u) == "AGGREGATOR"]
    shortener_urls   = [u for u in all_urls if classify_url(u) == "SHORTENER"]
    other_urls       = [u for u in all_urls if classify_url(u) == "OTHER"]

    # Priority for apply_link: official > aggregator > shortener > other > first url
    if official_urls:
        fields["apply_link"]    = official_urls[0][:500]
        fields["original_link"] = official_urls[0][:500]   # already terminal
    elif aggregator_urls:
        fields["apply_link"]    = aggregator_urls[0][:500]
        # Keep any official URL found later in the same message as original_link
        if len(official_urls) > 0:
            fields["original_link"] = official_urls[0][:500]
        else:
            fields["original_link"] = "unresolved"  # needs fetching later
    elif shortener_urls:
        fields["apply_link"]    = shortener_urls[0][:500]
        fields["original_link"] = "unresolved"
    elif other_urls:
        fields["apply_link"]    = other_urls[0][:500]
        fields["original_link"] = other_urls[0][:500]
    elif all_urls:
        fields["apply_link"]    = all_urls[0][:500]
        fields["original_link"] = "unresolved"

    # If the message has BOTH an aggregator link AND an official link,
    # promote the official one to original_link regardless of order
    if official_urls and aggregator_urls:
        fields["apply_link"]    = aggregator_urls[0][:500]  # keep aggregator as apply_link
        fields["original_link"] = official_urls[0][:500]    # official is the real destination

    # ── Inline context clues: look for labelled apply links ───────────────────
    # e.g. "Apply Link: https://..." or "Click here to Apply: https://..."
    labelled = re.findall(
        r"(?:apply\s*(?:link|now|here)|click\s*here)\s*[:\-]?\s*(https?://[^\s)>\]'\"]+)",
        text, re.IGNORECASE
    )
    labelled = [u.rstrip(".,;:!?'\"") for u in labelled]
    for u in labelled:
        cat = classify_url(u)
        if cat == "OFFICIAL":
            fields["original_link"] = u[:500]
            break
        elif cat == "AGGREGATOR" and "apply_link" not in fields:
            fields["apply_link"] = u[:500]

    email_match = re.search(r"([\w\.\-]+@[\w\.\-]+\.\w+)", text, re.IGNORECASE)
    if email_match:
        fields["email"] = email_match.group(1).strip()[:200]

    # Map fields to their corresponding label patterns
    patterns = {
        "title": [r"role", r"position", r"designation", r"job\s*title", r"post\s*name", r"job\s*role"],
        "company": [r"company\s*name", r"company", r"organi[sz]ation", r"employer", r"conducted\s*by"],
        "location": [r"location", r"city", r"based\s*in", r"work\s*location", r"job\s*location"],
        "experience": [r"experience", r"exp", r"eligibility", r"batch(?:es)?", r"qualification"],
        "skills": [r"skills", r"key\s*skills", r"requirements", r"knowledge", r"tech\s*stack", r"stack", r"skills\s*required"],
        "salary": [r"salary", r"ctc", r"package", r"package\s*expected"],
    }
    
    lines = text.split("\n")
    for line in lines:
        line_stripped = line.strip()
        if not line_stripped:
            continue
            
        for field, keywords in patterns.items():
            if field in fields:
                continue
                
            kw_pattern = "|".join(keywords)
            # Match label followed by colon/dash and then the value.
            # Stop matching if we hit a common emoji used as bullet points
            pattern = rf"(?:{kw_pattern})\s*[:\-]\s*([^💼📍🎓💰💵🚀🚨🔥📱✉️📧👤🏢ℹ️⏳🕒\n\|]+)"
            match = re.search(pattern, line_stripped, re.IGNORECASE)
            if match:
                val = match.group(1).strip()
                val = re.sub(r"^[:\-\s]+|[:\-\s]+$", "", val)
                if val:
                    fields[field] = val[:200]
                    
    # Fallback heuristic for title
    if "title" not in fields:
        hiring_patterns = [
            r"hiring\s+(?:freshers?\s+for\s+|for\s+)?([^💼📍🎓💰💵🚀🚨🔥\n\-\|]+)",
            r"opportunity\s+for\s+([^💼📍🎓💰💵🚀🚨🔥\n\-\|]+)",
            r"recruitment\s+202\d\s+\|\s+([^💼📍🎓💰💵🚀🚨🔥\n\-\|]+)",
        ]
        for hp in hiring_patterns:
            h_match = re.search(hp, text, re.IGNORECASE)
            if h_match:
                val = h_match.group(1).strip()
                if val and len(val) < 80 and not any(k in val.lower() for k in ["candidate", "associate", "opportunity"]):
                    fields["title"] = val
                    break

    return fields


def run_paddle_ocr_for_job(image_path: str) -> str:
    try:
        from paddleocr import PaddleOCR
        ocr = PaddleOCR(use_angle_cls=True, lang='en', show_log=False)
        result = ocr.ocr(image_path, cls=True)
        if not result or not result[0]:
            return ""
        texts = [line[1][0] for line in result[0]]
        return "\n".join(texts)
    except Exception:
        return ""


def build_job_record(message, channel_name: str, keywords, ocr_text: str = "") -> dict | None:
    text = (message.message or "") + "\n" + ocr_text
    if not looks_like_job_post(text, keywords):
        return None

    fields = extract_fields(text)
    return {
        "channel":       channel_name,
        "message_id":    message.id,
        "date":          message.date.astimezone(timezone.utc).isoformat() if message.date else None,
        "title":         fields.get("title"),
        "company":       fields.get("company"),
        "location":      fields.get("location"),
        "experience":    fields.get("experience"),
        "skills":        fields.get("skills"),
        "salary":        fields.get("salary"),
        "apply_link":    fields.get("apply_link"),
        "original_link": fields.get("original_link", "unresolved"),
        "email":         fields.get("email"),
        "raw_text":      text.strip().replace("\n", " ")[:1000],
        "message_link":  f"https://t.me/{channel_name}/{message.id}" if not channel_name.startswith("-") else None,
    }


def save_records(records: list[dict], days: int = 3):
    if not records:
        print("No job-like messages found.")
        return

    # Load existing from PostgreSQL instead of JSON
    existing = load_recent_records_from_postgres(days)

    # Calculate cutoff date in UTC (since dates are saved in UTC ISO format)
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    # Filter both existing and incoming records to keep only recent ones
    recent_records = []
    for r in existing + records:
        date_str = r.get("date")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str)
                if dt.tzinfo is None:
                    dt = dt.replace(tzinfo=timezone.utc)
                if dt >= cutoff_date:
                    recent_records.append(r)
            except ValueError:
                continue

    # Deduplicate the entire set
    deduplicated = []
    seen_apply_links = set()
    seen_texts = set()
    seen_title_company = set()

    # Sort recent_records by date descending to prioritize keeping the latest duplicate
    recent_records.sort(key=lambda x: x.get("date") or "", reverse=True)

    for r in recent_records:
        apply_link = r.get("apply_link")
        raw_text = r.get("raw_text", "")
        # Normalize text to check for duplicates (ignore emojis, whitespace, punctuation)
        norm_text = re.sub(r"[^\w\s]", "", raw_text).strip().lower()
        norm_text = re.sub(r"\s+", " ", norm_text)

        title = (r.get("title") or "").strip().lower()
        company = (r.get("company") or "").strip().lower()
        
        is_dup = False
        
        # Deduplicate by apply_link
        if apply_link and apply_link != "N/A":
            if apply_link in seen_apply_links:
                is_dup = True
            else:
                seen_apply_links.add(apply_link)
                
        # Deduplicate by identical text content
        if norm_text:
            if norm_text in seen_texts:
                is_dup = True
            else:
                seen_texts.add(norm_text)

        # Deduplicate by title & company combination
        if title and company and title != "n/a" and company != "n/a":
            title_comp = (title, company)
            if title_comp in seen_title_company:
                is_dup = True
            else:
                seen_title_company.add(title_comp)

        if not is_dup:
            deduplicated.append(r)

    # Sort back to date ascending for storage
    deduplicated.sort(key=lambda x: x.get("date") or "")

    # Save to PostgreSQL database
    save_records_to_postgres(deduplicated)

    new_saved_count = len(deduplicated) - len(existing)
    print(f"Saved {max(0, new_saved_count)} new job post(s). Total deduplicated in PostgreSQL: {len(deduplicated)}.")


def fetch_original_link(url: str) -> str:
    """
    Fetch an aggregator/shortener page and extract the best real apply link.
    5-pass priority:
      1. OFFICIAL link whose anchor text has an apply keyword
      2. Any OFFICIAL-classified link on the page
      3. Raw HTML scan for official-pattern URLs (catches JS-encoded hrefs)
      4. External non-aggregator/non-skip link near apply keyword
      5. First external non-aggregator/non-skip outbound link (last resort)
    """
    import re as _re

    APPLY_KWS = {
        "apply", "apply now", "apply here", "apply link", "apply fast",
        "click here", "register", "apply online", "official link",
        "direct link", "official apply", "apply for",
    }

    class LinkParser(HTMLParser):
        def __init__(self, base):
            super().__init__()
            self.base  = base
            self.links = []   # [(abs_href, anchor_text_lower)]
            self._href = None
            self._text = ""
            self._in_a = False

        def handle_starttag(self, tag, attrs):
            if tag == "a":
                self._in_a = True
                self._text = ""
                d = dict(attrs)
                self._href = d.get("href") or d.get("data-href") or ""

        def handle_endtag(self, tag):
            if tag == "a" and self._in_a:
                self._in_a = False
                if self._href:
                    try:
                        abs_href = urllib.parse.urljoin(self.base, self._href)
                        self.links.append((abs_href, self._text.strip().lower()))
                    except Exception:
                        pass
                self._href = None
                self._text = ""

        def handle_data(self, data):
            if self._in_a:
                self._text += data

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            raw_html = resp.read(300_000).decode("utf-8", errors="ignore")
    except Exception:
        return "unresolved"

    base_host = urllib.parse.urlparse(url).netloc.lower().lstrip("www.")

    parser = LinkParser(url)
    try:
        parser.feed(raw_html)
    except Exception:
        pass

    def is_useful(href: str) -> bool:
        if not href or not href.startswith("http"):
            return False
        h = urllib.parse.urlparse(href).netloc.lower().lstrip("www.")
        if h == base_host:
            return False
        if classify_url(href) in ("SKIP",):
            return False
        return True

    links = [(h, t) for h, t in parser.links if is_useful(h)]

    def has_apply_kw(text: str) -> bool:
        return any(kw in text for kw in APPLY_KWS)

    # Pass 1: OFFICIAL link with apply keyword in anchor text
    for href, text in links:
        if classify_url(href) == "OFFICIAL" and has_apply_kw(text):
            return href

    # Pass 2: any OFFICIAL link on the page
    for href, text in links:
        if classify_url(href) == "OFFICIAL":
            return href

    # Pass 3: raw HTML scan (catches URLs in onclick / data attrs not in <a href>)
    raw_urls = _re.findall(r'https?://[^\s"\'<>\\]+', raw_html)
    for raw_url in raw_urls:
        raw_url = raw_url.rstrip(".,;)'\"")
        if classify_url(raw_url) == "OFFICIAL" and is_useful(raw_url):
            return raw_url

    # Pass 4: external non-aggregator link near apply text
    for href, text in links:
        cat = classify_url(href)
        if cat not in ("AGGREGATOR", "SHORTENER", "SKIP") and has_apply_kw(text):
            return href

    # Pass 5: first external non-aggregator/skip outbound link
    for href, text in links:
        cat = classify_url(href)
        if cat not in ("AGGREGATOR", "SHORTENER", "SKIP"):
            return href

    return "unresolved"


async def resolve_original_links():
    """
    Post-scan: for every job with original_link == 'unresolved',
    concurrently fetch the aggregator page and extract the real link.
    Saves progress to PostgreSQL database.
    """
    # Load all jobs from PostgreSQL instead of JSON
    jobs = load_all_jobs_from_postgres()
    if not jobs:
        print("No jobs found in PostgreSQL database to resolve.")
        return

    unresolved = [
        j for j in jobs
        if not j.get("original_link") or j.get("original_link") == "unresolved"
        if j.get("apply_link")
    ]
    if not unresolved:
        print("All original links already resolved.")
        return

    print(f"\nResolving {len(unresolved)} original link(s) — fetching aggregator pages concurrently...\n")

    loop = asyncio.get_running_loop()
    resolved_count = 0

    async def fetch_one(job):
        """Wrapper: fetch in thread pool and return (job, result)."""
        result = await loop.run_in_executor(None, fetch_original_link, job["apply_link"])
        return job, result

    tasks = [fetch_one(job) for job in unresolved]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    for item in results:
        if isinstance(item, Exception):
            continue
        job, result = item
        # Reject false positives — YouTube subscriptions, Telegram channels, etc.
        if not is_valid_original_link(result):
            result = "unresolved"
        job["original_link"] = result
        title = (job.get("title") or "")[:55] or job["apply_link"][:55]
        if result != "unresolved":
            resolved_count += 1
            print(f"  [OK]  {title}")
            print(f"        -> {result}")
        else:
            print(f"  [--]  {title}  (unresolved)")

    # Save to PostgreSQL database
    save_records_to_postgres(jobs)
    print(f"\nDone. Resolved {resolved_count} / {len(unresolved)} original links in PostgreSQL.\n")

def enrich_job_from_page(job: dict) -> dict:
    """
    Fetch the job's original_link page and extract richer metadata.
    Priority order for each field:
      1. JSON-LD JobPosting schema  (most accurate — used by Workday, Greenhouse, etc.)
      2. OpenGraph / meta tags
      3. <title> tag fallback
    Only overwrites a field if the new value is non-empty and more informative
    than the existing value (i.e. current value is missing or 'N/A').
    """
    import re as _re

    url = job.get("original_link", "")
    if not url or url == "unresolved" or not is_valid_original_link(url):
        return job

    # ── 0. Manual Overrides for SPA / Protected Sites ─────────────────────────
    MANUAL_OVER_MAP = {
        "https://app.joinsuperset.com/join/#/signup/student/jobprofiles/aa8dda8f-2e39-4377-bf46-a255f7f941e3": {
            "title": "Junior Management Trainee",
            "company": "Hexaware Technologies",
            "location": "Siruseri, Chennai",
            "experience": "Freshers / 2026 Batch (MBA)",
            "salary": "₹5.00 LPA",
            "skills": "Business Management, MBA, Communication, Client Relations"
        },
        "https://app.joinsuperset.com/join/#/signup/student/jobprofiles/a8af19f3-444e-43bd-8828-e8656f637a17": {
            "title": "Service Desk - Digital Workplace Practice",
            "company": "Cognizant",
            "location": "PAN India",
            "experience": "Freshers / 2025/2026 Batch (Any Degree)",
            "salary": "₹2.52 LPA",
            "skills": "IT Help Desk, Customer Support, Troubleshooting, Communication"
        },
        "https://www.virtusa.com/careers/in/bangalore/aims/software-engineer/creq255954": {
            "title": "GCP Tech Support Agent",
            "company": "Virtusa",
            "location": "Bangalore, Karnataka, India",
            "experience": "0-2 Years",
            "skills": "Google Cloud Platform, Compute Engine, IAM, VPC, GCP Certifications, Jira, ServiceNow"
        }
    }

    if url in MANUAL_OVER_MAP:
        updated = dict(job)
        for field, val in MANUAL_OVER_MAP[url].items():
            if val:
                updated[field] = val
        return updated

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
        "Accept-Encoding": "identity",
    }

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=12) as resp:
            html = resp.read(400_000).decode("utf-8", errors="ignore")
    except Exception:
        return job

    extracted = {}

    # ── 1. JSON-LD JobPosting schema ──────────────────────────────────────────
    ld_blocks = _re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html, _re.DOTALL | _re.IGNORECASE
    )
    for block in ld_blocks:
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        # Handle both single object and @graph array
        items = data if isinstance(data, list) else [data]
        for item in items:
            if isinstance(item, dict) and item.get("@type") in ("JobPosting", "jobPosting"):
                # Title
                if item.get("title"):
                    extracted["title"] = item["title"].strip()
                # Company
                org = item.get("hiringOrganization") or {}
                if isinstance(org, dict) and org.get("name"):
                    extracted["company"] = org["name"].strip()
                # Location
                def get_str_value(val) -> str:
                    if not val:
                        return ""
                    if isinstance(val, dict):
                        return str(val.get("name") or val.get("value") or next(iter(val.values()), ""))
                    return str(val)

                loc = item.get("jobLocation") or {}
                if isinstance(loc, list):
                    loc = loc[0] if loc else {}
                addr = loc.get("address") or {} if isinstance(loc, dict) else {}
                if isinstance(addr, list):
                    addr = addr[0] if addr else {}
                parts = [
                    get_str_value(addr.get("addressLocality", "")),
                    get_str_value(addr.get("addressRegion", "")),
                    get_str_value(addr.get("addressCountry", "")),
                ]
                loc_str = ", ".join(p for p in parts if p)
                if loc_str:
                    extracted["location"] = loc_str
                # Experience / qualifications
                exp = (
                    item.get("experienceRequirements") or
                    item.get("qualifications") or
                    item.get("educationRequirements") or ""
                )
                if isinstance(exp, dict):
                    exp = exp.get("description") or exp.get("name") or ""
                if exp:
                    extracted["experience"] = str(exp).strip()[:200]
                # Skills
                skills = item.get("skills") or item.get("competencies") or ""
                if isinstance(skills, list):
                    skills = ", ".join(str(s) for s in skills)
                if skills:
                    extracted["skills"] = str(skills).strip()[:300]
                # Salary
                sal = item.get("baseSalary") or item.get("salaryCurrency") or ""
                if isinstance(sal, dict):
                    val = sal.get("value") or {}
                    if isinstance(val, dict):
                        mn = val.get("minValue", "")
                        mx = val.get("maxValue", "")
                        cur = sal.get("currency", "")
                        sal = f"{cur} {mn}–{mx}".strip() if mn or mx else ""
                    else:
                        sal = str(val)
                if sal:
                    extracted["salary"] = str(sal).strip()
                break
        if extracted.get("title"):
            break  # Found a JobPosting block — stop searching

    # ── 2. OpenGraph / standard meta tags ─────────────────────────────────────
    def get_meta(prop_attr: str, value: str) -> str:
        """Extract <meta property="X" content="Y"> or <meta name="X" content="Y">."""
        pattern = (
            rf'<meta[^>]+{prop_attr}=["\']' + _re.escape(value) +
            r'["\'][^>]+content=["\']([^"\']+)["\']|'
            rf'<meta[^>]+content=["\']([^"\']+)["\'][^>]+{prop_attr}=["\']' +
            _re.escape(value) + r'["\']'
        )
        m = _re.search(pattern, html, _re.IGNORECASE)
        if m:
            return (m.group(1) or m.group(2) or "").strip()
        return ""

    if not extracted.get("title"):
        og_title = get_meta("property", "og:title") or get_meta("name", "title")
        if og_title:
            extracted["title"] = og_title

    if not extracted.get("company"):
        site_name = get_meta("property", "og:site_name")
        if site_name:
            extracted["company"] = site_name

    # ── 3. <title> tag fallback ───────────────────────────────────────────────
    if not extracted.get("title"):
        m = _re.search(r"<title[^>]*>([^<]+)</title>", html, _re.IGNORECASE)
        if m:
            raw_title = m.group(1).strip()
            # Strip common suffixes like " | Company" or " - Careers"
            for sep in [" | ", " - ", " — ", " – ", " / "]:
                if sep in raw_title:
                    raw_title = raw_title.split(sep)[0].strip()
                    break
            extracted["title"] = raw_title

    # ── 4. Domain to Company Name Mapping ─────────────────────────────────────
    domain_to_company = {
        "quest-global.com": "Quest Global",
        "deloitte.com": "Deloitte USI",
        "accenture.com": "Accenture",
        "wipro.com": "Wipro",
        "infosys.com": "Infosys",
        "tcs.com": "TCS",
        "hcltech.com": "HCLTech",
        "capgemini.com": "Capgemini",
        "cognizant.com": "Cognizant",
        "amazon.jobs": "Amazon",
        "amazon.com": "Amazon",
        "google.com": "Google",
        "microsoft.com": "Microsoft",
        "yello.co": "EY",
        "peoplestrong.com": "L&T (Larsen & Toubro)",
        "oraclecloud.com": "Oracle",
        "ashbyhq.com": "Ashby",
        "sap.com": "SAP",
        "icims.com": "HealthEdge",
        "icicicareers.com": "ICICI Bank",
        "cisco.com": "Cisco",
        "db.com": "Deutsche Bank",
        "jio.com": "Jio",
        "param.ai": "Maruti Suzuki",
        "medpace.com": "Medpace",
        "csod.com": "Cornerstone",
        "micron.com": "Micron",
        "hp.com": "HP",
        "salesforce.com": "Salesforce",
        "smartrecruiters.com": "NielsenIQ"
    }

    if not extracted.get("company"):
        try:
            from urllib.parse import urlparse
            host = urlparse(url).netloc.lower().lstrip("www.")
            for domain, comp_name in domain_to_company.items():
                if domain in host:
                    extracted["company"] = comp_name
                    break
        except Exception:
            pass

    # ── 5. HTML Body Text Parsing Fallback (Skills, Exp, Location, Salary) ───
    try:
        # Strip script, style, and HTML tags to get pure visible text
        text_content = _re.sub(r'<script.*?</script>', ' ', html, flags=_re.DOTALL | _re.IGNORECASE)
        text_content = _re.sub(r'<style.*?</style>', ' ', text_content, flags=_re.DOTALL | _re.IGNORECASE)
        text_content = _re.sub(r'<[^>]+>', ' ', text_content)
        text_content = _re.sub(r'\s+', ' ', text_content).strip()

        # A. Experience extraction
        if not extracted.get("experience"):
            exp_patterns = [
                r'\b\d+\s*-\s*\d+\s*years?\b',
                r'\b\d+\s*to\s*\d+\s*years?\b',
                r'\b\d+\s*\+\s*years?\b'
            ]
            found_exps = []
            for pat in exp_patterns:
                found_exps.extend(_re.findall(pat, text_content, _re.IGNORECASE))
            
            clean_exps = []
            for exp_str in found_exps:
                digits = [int(s) for s in _re.findall(r'\d+', exp_str)]
                if all(d < 15 for d in digits):
                    clean_exps.append(exp_str)
                    
            if clean_exps:
                extracted["experience"] = clean_exps[0]
            elif any(w in text_content.lower() for w in ["fresher", "freshers", "university graduate", "entry level", "campus hiring"]):
                extracted["experience"] = "Freshers"

        # B. Skills extraction
        skill_db = [
            "Python", "Java", "JavaScript", "TypeScript", "SQL", "HTML", "CSS", "React",
            "Angular", "Vue", "Node.js", "Django", "Flask", "Spring Boot", "Git", "Docker",
            "Kubernetes", "AWS", "Azure", "GCP", "C++", "C#", "Excel", "Word", "PowerPoint",
            "Salesforce", "Testing", "Manual Testing", "Automation Testing", "Selenium", "Linux",
            "Jira", "ServiceNow", "Smartsheet", "Project Management", "UI/UX", "Machine Learning",
            "Deep Learning", "Generative AI", "NLP", "C", "Go", "Kotlin", "Swift", "Flutter"
        ]
        
        found_skills = []
        for s in skill_db:
            escaped = _re.escape(s)
            if s in ("C++", "C#"):
                pattern = r'\b' + escaped + r'(?!\w)'
            else:
                pattern = r'\b' + escaped + r'\b'
            if _re.search(pattern, text_content, _re.IGNORECASE):
                found_skills.append(s)
                
        if found_skills:
            extracted["skills"] = ", ".join(found_skills)

        # C. Location fallback extraction
        if not extracted.get("location"):
            cities = [
                "Bengaluru", "Bangalore", "Hyderabad", "Chennai", "Pune", "Mumbai",
                "Noida", "Gurgaon", "Gurugram", "Delhi", "Kochi", "Trivandrum", "Kolkata",
                "Ahmedabad", "Siruseri", "Virtual", "Remote"
            ]
            found_cities = []
            for city in cities:
                if _re.search(r'\b' + _re.escape(city) + r'\b', text_content, _re.IGNORECASE):
                    found_cities.append(city)
            if found_cities:
                mapped_cities = ["Bengaluru" if c == "Bangalore" else c for c in found_cities]
                mapped_cities = list(dict.fromkeys(mapped_cities))
                extracted["location"] = ", ".join(mapped_cities[:3])

        # D. Salary fallback extraction
        if not extracted.get("salary"):
            sal_matches = _re.findall(r'\b\d+(?:\.\d+)?\s*-\s*\d+(?:\.\d+)?\s*LPA\b|\b\d+(?:\.\d+)?\s*Lakhs?\b', text_content, _re.IGNORECASE)
            if sal_matches:
                extracted["salary"] = sal_matches[0]

    except Exception:
        pass

    def better(new_val: str, old_val) -> bool:
        if not new_val:
            return False
        new_clean = str(new_val).strip().lower()
        if new_clean in ("", "n/a", "none", "null", "undefined"):
            return False
        return True

    updated = dict(job)
    for field in ("title", "company", "location", "experience", "skills", "salary"):
        if better(extracted.get(field, ""), updated.get(field)):
            updated[field] = extracted[field]

    return updated


async def enrich_all_jobs():
    """
    For every job in PostgreSQL that has a valid original_link,
    fetch the real page and update title/company/location/experience/skills/salary.
    Runs up to 10 fetches concurrently. Saves results back to PostgreSQL.
    """
    # Load jobs from PostgreSQL instead of JSON
    jobs = load_all_jobs_from_postgres()
    if not jobs:
        print("No jobs found in PostgreSQL database to enrich.")
        return

    to_enrich = [
        j for j in jobs
        if is_valid_original_link(j.get("original_link", ""))
    ]
    if not to_enrich:
        print("No jobs with valid original links to enrich.")
        return

    print(f"\nEnriching {len(to_enrich)} job(s) from original pages...\n")

    loop = asyncio.get_running_loop()
    enriched_count = 0

    async def enrich_one(job):
        return await loop.run_in_executor(None, enrich_job_from_page, job)

    tasks = [enrich_one(j) for j in to_enrich]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Replace enriched jobs back into the full jobs list
    enriched_map = {}
    for item in results:
        if isinstance(item, dict):
            key = (item.get("channel"), item.get("message_id"))
            enriched_map[key] = item

    updated_count = 0
    for i, job in enumerate(jobs):
        key = (job.get("channel"), job.get("message_id"))
        if key in enriched_map:
            new_job = enriched_map[key]
            # Count as updated if any field changed
            for f in ("title", "company", "location", "experience", "skills", "salary"):
                if new_job.get(f) != job.get(f):
                    updated_count += 1
                    break
            jobs[i] = new_job
            title = (new_job.get("title") or "")[:50]
            company = (new_job.get("company") or "N/A")[:30]
            print(f"  [✓] {title} — {company}")

    # Save to PostgreSQL database
    save_records_to_postgres(jobs)
    print(f"\nEnrichment complete. {updated_count} job(s) updated in PostgreSQL.\n")


async def scan_channels(client: TelegramClient, config: dict, days: int = 3):
    keywords = config.get("keywords", DEFAULT_KEYWORDS)
    limit = config.get("history_limit", 300)
    all_records = []

    # Calculate cutoff date in UTC
    cutoff_date = datetime.now(timezone.utc) - timedelta(days=days)

    for channel in config["channels"]:
        try:
            entity = await client.get_entity(channel)
        except Exception as e:
            print(f"Could not access channel '{channel}': {e}")
            continue

        channel_name = getattr(entity, "username", None) or str(getattr(entity, "id", channel))
        print(f"Scanning '{channel_name}' (up to {limit} messages, cutoff: {days} days)...")

        count = 0
        async for message in client.iter_messages(entity, limit=limit):
            # Check message date limit
            if message.date and message.date < cutoff_date:
                break
            ocr_text = ""
            if message.media and hasattr(message.media, "photo"):
                try:
                    temp_path = f"media_{channel_name}_{message.id}.jpg"
                    await client.download_media(message, file=temp_path)
                    
                    loop = asyncio.get_running_loop()
                    ocr_text = await loop.run_in_executor(None, run_paddle_ocr_for_job, temp_path)
                    
                    if os.path.exists(temp_path):
                        os.remove(temp_path)
                except Exception as e:
                    print(f"  [ERROR] Image download/OCR failed: {e}")
                    
            record = build_job_record(message, channel_name, keywords, ocr_text=ocr_text)
            if record:
                all_records.append(record)
                count += 1
        print(f"  -> {count} job-like message(s) found in '{channel_name}'.")

    save_records(all_records, days=days)

    # Phase 2: resolve aggregator pages → get real apply links
    await resolve_original_links()

    # Phase 3: fetch real job pages → enrich all fields
    await enrich_all_jobs()


async def listen_channels(client: TelegramClient, config: dict):
    keywords = config.get("keywords", DEFAULT_KEYWORDS)
    channels = config["channels"]

    entities = []
    for channel in channels:
        try:
            entity = await client.get_entity(channel)
            entities.append(entity)
        except Exception as e:
            print(f"Could not access channel '{channel}': {e}")

    if not entities:
        print("No valid channels to listen to. Check your config.")
        return

    print(f"Listening for new job posts on {len(entities)} channel(s). Press Ctrl+C to stop.")

    @client.on(events.NewMessage(chats=entities))
    async def handler(event):
        channel_name = getattr(event.chat, "username", None) or str(event.chat_id)
        ocr_text = ""
        if event.message.media and hasattr(event.message.media, "photo"):
            try:
                temp_path = f"media_{channel_name}_{event.message.id}.jpg"
                await client.download_media(event.message, file=temp_path)
                
                loop = asyncio.get_running_loop()
                ocr_text = await loop.run_in_executor(None, run_paddle_ocr_for_job, temp_path)
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            except Exception as e:
                print(f"  [ERROR] Image download/OCR failed: {e}")
                
        record = build_job_record(event.message, channel_name, keywords, ocr_text=ocr_text)
        if record:
            save_records([record], days=3)
            print(f"[NEW JOB] {record.get('title') or record['raw_text'][:80]} — {channel_name}")

    await client.run_until_disconnected()


async def display_jobs(days: int):
    import sys
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

    # Load all jobs from PostgreSQL instead of JSON
    jobs = load_all_jobs_from_postgres()
    if not jobs:
        print("No jobs found in PostgreSQL database. Please run the scanner first.")
        return

    from datetime import datetime, timedelta
    
    # Calculate target dates in YYYY-MM-DD format
    now = datetime.now()
    target_dates = [(now - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]

    filtered_jobs = []
    for job in jobs:
        date_str = job.get("date")
        if date_str:
            try:
                dt = datetime.fromisoformat(date_str)
                date_only = dt.strftime("%Y-%m-%d")
                if date_only in target_dates:
                    filtered_jobs.append(job)
            except ValueError:
                continue

    # Sort filtered_jobs by date descending
    filtered_jobs.sort(key=lambda x: x.get("date", ""), reverse=True)

    if not filtered_jobs:
        print(f"\n=================== NO JOBS FOUND FOR THE LAST {days} DAYS ===================\n")
        return

    # Extract all unique apply links to verify concurrently
    urls_to_check = []
    for job in filtered_jobs:
        link = job.get("apply_link")
        if link and link != "N/A" and link.startswith("http"):
            urls_to_check.append(link)

    print(f"\nVerifying {len(urls_to_check)} job application links concurrently...")
    
    # Perform link validation
    import concurrent.futures
    
    def check_url_status(url):
        import urllib.request
        import urllib.error
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=5) as response:
                return response.status
        except urllib.error.HTTPError as e:
            return e.code
        except Exception:
            return "Dead/Error"

    url_status_map = {}
    if urls_to_check:
        loop = asyncio.get_running_loop()
        with concurrent.futures.ThreadPoolExecutor(max_workers=15) as executor:
            tasks = [
                loop.run_in_executor(executor, check_url_status, url)
                for url in urls_to_check
            ]
            results = await asyncio.gather(*tasks)
            for url, status in zip(urls_to_check, results):
                url_status_map[url] = status

    print(f"\n=================== JOBS FROM THE LAST {days} DAYS ({len(filtered_jobs)} FOUND) ===================")
    for idx, job in enumerate(filtered_jobs, 1):
        date_val = job.get("date", "N/A")
        try:
            dt = datetime.fromisoformat(date_val)
            date_formatted = dt.strftime("%Y-%m-%d %H:%M:%S")
        except ValueError:
            date_formatted = date_val

        channel = job.get("channel", "N/A")
        title = job.get("title") or "N/A"
        company = job.get("company") or "N/A"
        location = job.get("location") or "N/A"
        experience = job.get("experience") or "N/A"
        skills = job.get("skills") or "N/A"
        
        apply_link    = job.get("apply_link")
        original_link = job.get("original_link") or "unresolved"
        link = apply_link or job.get("message_link") or job.get("email") or "N/A"

        status_indicator = ""
        if apply_link and apply_link in url_status_map:
            status = url_status_map[apply_link]
            if isinstance(status, int) and 200 <= status < 300:
                status_indicator = " [🟢 Active]"
            else:
                status_indicator = f" [🔴 Dead/Error {status}]"

        # Show the verified real apply link if different from the aggregator link
        if original_link and original_link not in ("unresolved", apply_link):
            real_link_line = f"    Real Apply: {original_link}"
        elif original_link == "unresolved":
            real_link_line = "    Real Apply: (unresolved — aggregator link above)"
        else:
            real_link_line = "    Real Apply: same as apply link"

        print(f"\n[{idx}] {date_formatted} | Channel: @{channel}")
        print(f"    Role:       {title}")
        print(f"    Company:    {company}")
        print(f"    Location:   {location}")
        print(f"    Experience: {experience}")
        print(f"    Skills:     {skills}")
        print(f"    Contact:    {link}{status_indicator}")
        print(real_link_line)
        raw_text_snippet = job.get("raw_text", "").strip()[:150]
        if len(job.get("raw_text", "")) > 150:
            raw_text_snippet += "..."
        print(f"    Summary:    {raw_text_snippet}")
    print("\n=================================================================================\n")


async def main():
    parser = argparse.ArgumentParser(description="Telegram Job Agent")
    parser.add_argument(
        "--mode",
        choices=["scan", "listen", "display", "enrich", "server"],
        default="scan",
        help=(
            "'scan' pulls recent Telegram history + resolves + enriches; "
            "'enrich' re-enriches existing jobs from their original pages; "
            "'listen' watches live for new posts; "
            "'display' prints recent jobs; "
            "'server' runs continuously with a port health-check for cloud deployment"
        )
    )
    parser.add_argument("--days", type=int, default=3,
                         help="Number of recent days to scan/display (default: 3)")
    parser.add_argument("--channel", type=str, default="",
                         help="Single channel username or ID to synchronize")
    parser.add_argument("--full", action="store_true",
                         help="Full re-scan: reset watermarks and re-fetch last 3 days from all channels")
    parser.add_argument("--workers", type=int, default=5,
                         help="Max parallel channels to scan at once (default: 5)")
    args = parser.parse_args()

    if args.mode == "display":
        await display_jobs(args.days)
        return

    if args.mode == "enrich":
        await enrich_all_jobs()
        await display_jobs(args.days)
        return

    config = load_config()
    import db
    db.init_db()

    # Generate a unique instance ID for leader election/handover during rolling deploys
    import uuid
    import sys
    import os
    my_instance_id = str(uuid.uuid4())
    print(f"[{datetime.now().isoformat()}] Instance ID: {my_instance_id}")
    db.register_instance(my_instance_id)

    # Check for other active instances in the cloud
    active_instances = db.get_active_instances()
    other_active = [inst for inst, stat in active_instances if inst != my_instance_id]

    if other_active:
        print(f"[{datetime.now().isoformat()}] Other active instances found: {other_active}. Requesting takeover...")
        for old_id in other_active:
            db.request_takeover(old_id)

        # Wait for the old instances to shut down
        wait_seconds = 0
        while wait_seconds < 30:
            active_instances = db.get_active_instances()
            other_active = [inst for inst, stat in active_instances if inst != my_instance_id]
            if not other_active:
                print(f"[{datetime.now().isoformat()}] Old instances stopped. Proceeding to connect to Telegram...")
                break
            print(f"[{datetime.now().isoformat()}] Waiting for old instances to release session lock (elapsed: {wait_seconds}s)...")
            await asyncio.sleep(2)
            wait_seconds += 2
        else:
            print(f"[{datetime.now().isoformat()}] Old instances did not exit. Proceeding anyway, but key conflict might occur.")

    from telethon.sessions import StringSession
    session_str = config.get("telegram_session_string", "")
    client = TelegramClient(StringSession(session_str), config["api_id"], config["api_hash"])
    await client.start(phone=config["phone"])

    # Save session string back to config.json if it was generated/updated during login
    new_session_str = client.session.save()
    if new_session_str != session_str:
        config["telegram_session_string"] = new_session_str
        with open(CONFIG_PATH, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

    # Start background heartbeat to handle future takeover requests gracefully
    async def periodic_heartbeat():
        while True:
            try:
                status = db.heartbeat_instance(my_instance_id)
                if status == "stopping":
                    print(f"[{datetime.now().isoformat()}] Takeover request received! Disconnecting and shutting down...")
                    db.unregister_instance(my_instance_id)
                    await client.disconnect()
                    os._exit(0)  # Immediate exit to kill process and release ports
            except Exception as e:
                print(f"[HEARTBEAT ERROR] {e}")
            await asyncio.sleep(2)

    heartbeat_task = asyncio.create_task(periodic_heartbeat())

    if args.mode == "scan":
        import telegram_sync
        channels = [args.channel] if args.channel else config.get("channels", [])
        if not channels:
            channels = load_channels_from_file()

        # Scan parameters — default = 3 days, but allow larger values
        full_scan   = args.full
        cutoff_days = args.days        # default = 3
        history_lim = 1500 if cutoff_days > 3 else 500
        max_workers = args.workers     # parallel channels (default 5)

        if full_scan:
            print(f"[FULL SCAN] Resetting watermarks for all {len(channels)} channels...")
            import db as _db
            _db.init_db()
            import psycopg2
            cfg = load_config()
            conn = psycopg2.connect(
                host=cfg["postgres"]["host"],
                port=cfg["postgres"]["port"],
                database=cfg["postgres"]["database"],
                user=cfg["postgres"]["user"],
                password=cfg["postgres"]["password"],
            )
            conn.autocommit = True
            cur = conn.cursor()
            cur.execute("UPDATE telegram_channels SET last_processed_message_id = 0")
            print(f"[FULL SCAN] Watermarks reset. Rows affected: {cur.rowcount}")
            cur.close(); conn.close()

        print(f"Starting {'FULL' if full_scan else 'incremental'} scan for "
              f"{len(channels)} channels | limit={history_lim} msgs | "
              f"window={cutoff_days} days | workers={max_workers}")

        # Semaphore-limited parallel scanning
        sem = asyncio.Semaphore(max_workers)

        async def scan_one(ch):
            async with sem:
                try:
                    await telegram_sync.sync_channel(
                        client, ch,
                        history_limit=history_lim,
                        cutoff_days=cutoff_days,
                        full=full_scan,
                    )
                except Exception as e:
                    print(f"[ERROR] Failed to sync channel '{ch}': {e}")

        await asyncio.gather(*[scan_one(ch) for ch in channels])

        # Run Retry Queue for any OCR_FAILED messages
        try:
            await telegram_sync.retry_ocr_failed_jobs(client)
        except Exception as e:
            print(f"[ERROR] Failed to run retry queue: {e}")
            
        await display_jobs(args.days)
    elif args.mode == "server":
        import os
        import telegram_sync
        
        async def handle_health_check(reader, writer):
            try:
                await reader.readuntil(b"\r\n\r\n")
            except Exception:
                pass
            response = (
                "HTTP/1.1 200 OK\r\n"
                "Content-Type: application/json\r\n"
                "Connection: close\r\n\r\n"
                '{"status":"healthy"}'
            )
            writer.write(response.encode("utf-8"))
            await writer.drain()
            writer.close()
            try:
                await writer.wait_closed()
            except Exception:
                pass

        port = int(os.environ.get("PORT", 8080))
        server = await asyncio.start_server(handle_health_check, "0.0.0.0", port)
        print(f"[{datetime.now().isoformat()}] Health check server listening on port {port}...")

        channels = config.get("channels", [])
        if not channels:
            channels = load_channels_from_file()

        async def periodic_scan():
            while True:
                print(f"[{datetime.now().isoformat()}] Starting periodic scan cycle for {len(channels)} channels...")
                for ch in channels:
                    try:
                        await telegram_sync.sync_channel(client, ch, history_limit=300, cutoff_days=args.days)
                    except Exception as e:
                        print(f"[ERROR] Failed to sync channel '{ch}': {e}")
                try:
                    await telegram_sync.retry_ocr_failed_jobs(client)
                except Exception as e:
                    print(f"[ERROR] Failed to run retry queue: {e}")
                
                print(f"[{datetime.now().isoformat()}] Sync cycle completed. Sleep for 10 minutes...")
                await asyncio.sleep(600)

        try:
            await asyncio.gather(
                server.serve_forever(),
                periodic_scan()
            )
        except (KeyboardInterrupt, asyncio.CancelledError):
            print("Server mode shutting down...")
        finally:
            server.close()
            await server.wait_closed()
    else:
        await listen_channels(client, config)

    await client.disconnect()



if __name__ == "__main__":
    asyncio.run(main())
