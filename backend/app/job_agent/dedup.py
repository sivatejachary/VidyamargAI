import hashlib
from db import get_db_connection, load_config

def generate_job_hash(title: str, company: str, location: str, apply_link: str) -> str:
    norm_url = (apply_link or "").strip().lower()
    return hashlib.sha256(norm_url.encode("utf-8")).hexdigest()

def is_duplicate_job(job_hash: str) -> bool:
    config = load_config()
    table_name = config.get("postgres", {}).get("table_name", "jobs")
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute(f"SELECT 1 FROM {table_name} WHERE job_hash = %s LIMIT 1;", (job_hash,))
        dup = cursor.fetchone() is not None
    except Exception:
        dup = False
    finally:
        cursor.close()
        conn.close()
    return dup
