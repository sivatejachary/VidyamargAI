import psycopg2

DB_CONFIG = {
    "host": "thomas.proxy.rlwy.net",
    "port": 20637,
    "database": "Vidyamargai",
    "user": "postgres",
    "password": "qPKoMqtzapoyltHQVdheOKyldfbnYrPH"
}

ALTER_TABLE_SQL = """
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_id SERIAL;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS channel VARCHAR(100);
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS message_id INTEGER;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS date TIMESTAMPTZ;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS company TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS experience TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS skills TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS salary TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS apply_link TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS original_link TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS email TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS message_link TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS raw_text TEXT;
ALTER TABLE jobs ADD COLUMN IF NOT EXISTS job_hash VARCHAR(64) UNIQUE;
"""

TRIGGER_SQL = """
CREATE OR REPLACE FUNCTION sync_jobs_columns()
RETURNS TRIGGER AS $$
BEGIN
    NEW.company_name := COALESCE(NEW.company_name, NEW.company, 'Tech Company');
    NEW.description := COALESCE(NEW.description, NEW.raw_text, '');
    NEW.apply_url := COALESCE(NEW.apply_url, NEW.apply_link, '');
    NEW.job_url := COALESCE(NEW.job_url, NEW.original_link, NEW.apply_link, '');
    NEW.posted_at := COALESCE(NEW.posted_at, NEW.date, CURRENT_TIMESTAMP);
    NEW.created_at := COALESCE(NEW.created_at, NEW.date, CURRENT_TIMESTAMP);
    
    -- Heuristics
    IF NEW.location IS NOT NULL THEN
        NEW.is_remote := (LOWER(NEW.location) LIKE '%remote%' OR LOWER(NEW.location) LIKE '%wfh%');
        NEW.is_hybrid := (LOWER(NEW.location) LIKE '%hybrid%');
    END IF;
    
    -- Skills string to JSON array
    IF NEW.skills IS NOT NULL AND (NEW.required_skills IS NULL OR NEW.required_skills::text = '[]') THEN
        NEW.required_skills := (
            SELECT COALESCE(json_agg(trim(s)), '[]'::json)
            FROM regexp_split_to_table(NEW.skills, ',') s 
            WHERE trim(s) <> ''
        );
        IF NEW.required_skills IS NULL THEN
            NEW.required_skills := '[]'::json;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_sync_jobs_columns ON jobs;
CREATE TRIGGER trigger_sync_jobs_columns
BEFORE INSERT OR UPDATE ON jobs
FOR EACH ROW
EXECUTE FUNCTION sync_jobs_columns();
"""

def main():
    print("Connecting to local thomas database to set up trigger and columns...")
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        conn.autocommit = True
        cur = conn.cursor()
        
        print("Adding missing crawler columns to 'jobs' table...")
        cur.execute(ALTER_TABLE_SQL)
        print("Columns added successfully.")
        
        print("Creating sync trigger...")
        cur.execute(TRIGGER_SQL)
        print("Sync trigger created successfully.")
        
        cur.close()
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    main()
