import os
import asyncio
from datetime import datetime, timezone, timedelta
from telethon import TelegramClient

import db
import ai_extractor
import dedup
from job_agent import fetch_original_link, enrich_job_from_page


# Social/noise domains — these are NEVER real apply pages
_NOISE_DOMAINS = [
    "youtube.com", "youtu.be", "wa.me", "whatsapp.com",
    "facebook.com", "instagram.com", "twitter.com", "x.com",
    "t.me", "telegram.me", "telegram.dog",
    "linkedin.com/in/",
    "yt.openinapp.co", "openinapp.co",
]

_SEEN_HASHES = set()


def _is_noise_url(url: str) -> bool:
    u = (url or "").lower()
    if "/premium" in u:
        return True
    return any(d in u for d in _NOISE_DOMAINS)


def load_seen_hashes_from_db():
    seen = set()
    try:
        conn = db.get_db_connection()
        cursor = conn.cursor()
        config = db.load_config()
        table_name = config.get("postgres", {}).get("table_name", "jobs")
        cursor.execute(f"SELECT job_hash FROM {table_name};")
        rows = cursor.fetchall()
        for r in rows:
            if r[0]:
                seen.add(r[0])
        cursor.close()
        conn.close()
    except Exception as e:
        print(f"[WARNING] Failed to load seen hashes from DB: {e}")
    return seen


# Initialise in-memory duplicates set from DB at startup
_SEEN_HASHES.update(load_seen_hashes_from_db())


async def process_single_job_link(
    job: dict, channel_name: str, msg_id: int, msg_date, merged_text: str
) -> dict:
    """Scrape, enrich, deduplicate and return the job record to be written in a database batch."""
    loop      = asyncio.get_running_loop()
    apply_url = job.get("apply_link", "")
    email     = job.get("email", "")
    has_email = bool(email and email != "N/A" and "@" in email)

    # ── Step 0: Drop if neither valid URL nor email is present ───────────────
    if (not apply_url or not apply_url.startswith("http")) and not has_email:
        print(f"  [SKIP] No valid URL or email in msg {msg_id}")
        return None
    if apply_url and _is_noise_url(apply_url):
        print(f"  [SKIP] Noise URL for msg {msg_id}: {apply_url[:60]}")
        return None

    # LEVEL 1: Quick check using the direct URL before any network resolution calls
    apply_to_hash_direct = apply_url if apply_url else (email or "no_link_or_email")
    j_hash_direct = dedup.generate_job_hash(None, None, None, apply_to_hash_direct)
    if j_hash_direct in _SEEN_HASHES:
        print(f"  [DUP] Skipped duplicate direct URL: {apply_to_hash_direct}")
        return None

    original_url = "unresolved"
    
    # ── Step 1: Resolve URL → scrape landing page for title/company ───────────
    if apply_url and apply_url.startswith("http"):
        original_url = await loop.run_in_executor(None, fetch_original_link, apply_url)
        
        # LEVEL 2: Quick check using the resolved URL before scraping the page
        if original_url != "unresolved":
            if _is_noise_url(original_url):
                print(f"  [SKIP] Resolved URL is noise: {original_url[:60]}")
                return None
            j_hash_resolved = dedup.generate_job_hash(None, None, None, original_url)
            if j_hash_resolved in _SEEN_HASHES:
                print(f"  [DUP] Skipped duplicate resolved URL: {original_url}")
                return None

            job_stub = {
                "apply_link":    apply_url,
                "original_link": original_url,
                "title":      job.get("title"),
                "company":    job.get("company"),
                "location":   job.get("location"),
                "experience": job.get("experience"),
                "skills":     job.get("skills"),
                "salary":     job.get("salary"),
                "email":      job.get("email"),
            }
            enriched = await loop.run_in_executor(
                None, enrich_job_from_page, job_stub
            )
            for k in ("title", "company", "location", "experience",
                      "skills", "salary", "email", "apply_link"):
                job[k] = enriched[k]

    # ── Step 2: Save regardless of N/A title/company ─────────────────────────
    title   = job.get("title")   or "N/A"
    company = job.get("company") or "N/A"

    apply_to_hash = original_url if original_url != "unresolved" else job.get("apply_link")
    if not apply_to_hash or apply_to_hash == "N/A":
        apply_to_hash = email or "no_link_or_email"

    j_hash = dedup.generate_job_hash(None, None, None, apply_to_hash)

    if j_hash in _SEEN_HASHES:
        print(f"  [DUP] Skipped duplicate URL: {apply_to_hash}")
        return None

    # Construct Job record
    job_record = {
        "channel": channel_name,
        "message_id": msg_id,
        "date": msg_date.isoformat() if msg_date else None,
        "title": job.get("title"),
        "company": job.get("company"),
        "location": job.get("location"),
        "experience": job.get("experience"),
        "skills": job.get("skills"),
        "salary": job.get("salary"),
        "apply_link": job.get("apply_link"),
        "original_link": original_url,
        "email": job.get("email"),
        "message_link": (
            f"https://t.me/{channel_name}/{msg_id}"
            if not str(channel_name).startswith("-") else None
        ),
        "raw_text": merged_text,
    }
    
    _SEEN_HASHES.add(j_hash)
    return job_record


async def sync_channel(
    client: TelegramClient,
    channel_selector: str,
    history_limit: int = 500,
    cutoff_days: int = 3,
    full: bool = False,
):
    """
    Synchronise one Telegram channel (direct batch insertion to PostgreSQL).
    """
    try:
        entity = await client.get_entity(channel_selector)
    except Exception as e:
        print(f"[ERROR] Could not resolve channel '{channel_selector}': {e}")
        return

    channel_id   = str(entity.id)
    channel_name = getattr(entity, "username", None) or getattr(entity, "title", channel_selector)

    # Watermark tracking (keep metadata in DB to allow incremental runs!)
    last_processed_id = 0 if full else db.get_channel_state(channel_id)
    print(f"Sync starting for '{channel_name}' (ID: {channel_id}). "
          f"Watermark: {last_processed_id} | limit={history_limit} | days={cutoff_days}")

    cutoff_date = datetime.now(timezone.utc) - timedelta(days=cutoff_days)
    db.update_channel_state(channel_id, channel_name, last_processed_id, "active")

    # Fetch messages newer than watermark and within cutoff window
    messages = []
    async for msg in client.iter_messages(entity, limit=history_limit):
        if msg.date and msg.date < cutoff_date:
            break
        if msg.id > last_processed_id:
            messages.append(msg)

    messages.reverse()  # chronological order

    if not messages:
        print(f"  -> '{channel_name}' is already up-to-date.")
        return

    print(f"  -> Found {len(messages)} new message(s) in '{channel_name}'.")

    config = load_config_temp()
    gemini_key = config.get("gemini", {}).get("api_key", "")

    loop = asyncio.get_running_loop()
    channel_jobs = []

    for msg in messages:
        msg_id   = msg.id
        msg_text = msg.message or ""
        msg_date = msg.date.astimezone(timezone.utc) if msg.date else None

        try:
            merged_text = msg_text.strip()
            
            # Log raw message in DB
            media_count = 1 if msg.media else 0
            await loop.run_in_executor(
                None, db.insert_raw_message,
                channel_id, msg_id, msg_date, merged_text, media_count
            )

            if not merged_text:
                await loop.run_in_executor(None, db.mark_message_processed, channel_id, msg_id, "INVALID")
                db.update_channel_state(channel_id, channel_name, msg_id, "active")
                continue

            extracted_list = ai_extractor.extract_job_details_with_ai(merged_text, gemini_key)

            if not extracted_list:
                await loop.run_in_executor(None, db.mark_message_processed, channel_id, msg_id, "INVALID")
                db.update_channel_state(channel_id, channel_name, msg_id, "active")
                continue

            # LEVEL 3: Group or filter duplicate URLs within this single Telegram message
            seen_msg_urls = set()
            unique_jobs_to_process = []
            for job in extracted_list:
                url = job.get("apply_link", "").strip().lower()
                if not url:
                    email = job.get("email", "").strip().lower()
                    if email and email not in seen_msg_urls:
                        seen_msg_urls.add(email)
                        unique_jobs_to_process.append(job)
                elif url not in seen_msg_urls:
                    seen_msg_urls.add(url)
                    unique_jobs_to_process.append(job)

            # Process all unique job listings found in this message
            tasks = [
                process_single_job_link(
                    job, channel_name, msg_id, msg_date, merged_text
                )
                for job in unique_jobs_to_process
            ]
            results = await asyncio.gather(*tasks)
            
            for res in results:
                if res and isinstance(res, dict):
                    channel_jobs.append(res)
            
            # Determine the status for raw message
            final_status = "SAVED"
            if all(r is None for r in results):
                final_status = "DUPLICATE"
                
            await loop.run_in_executor(None, db.mark_message_processed, channel_id, msg_id, final_status)
            db.update_channel_state(channel_id, channel_name, msg_id, "active")

        except Exception as e:
            print(f"  [ERROR] Failed to process msg {msg_id} in '{channel_name}': {e}")
            import traceback; traceback.print_exc()
            db.update_channel_state(channel_id, channel_name, msg_id, "active")

    # Write all new jobs for this channel in a single batch to PostgreSQL!
    if channel_jobs:
        inserted = await loop.run_in_executor(None, db.upsert_jobs_batch, channel_jobs)
        print(f"  -> [BATCH SAVED TO DB] Saved {len(channel_jobs)} job(s) from '{channel_name}' directly to PostgreSQL.")


def load_config_temp():
    import json
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    try:
        with open(cfg_path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


async def retry_ocr_failed_jobs(client: TelegramClient):
    pass
