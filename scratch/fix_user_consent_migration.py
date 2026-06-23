import os
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@thomas.proxy.rlwy.net:20637/Vidyamargai"
engine = create_engine(DATABASE_URL)

def run_migration():
    # 1. Inspect existing columns
    with engine.connect() as conn:
        print("Fetching existing columns of user_consents...")
        res = conn.execute(text("SELECT column_name, data_type FROM information_schema.columns WHERE table_name = 'user_consents';"))
        columns = {row[0]: row[1] for row in res}
        print("Current columns in user_consents:", columns)

        # 2. Add revoked_at if missing
        if "revoked_at" not in columns:
            print("Adding revoked_at column...")
            conn.execute(text("ALTER TABLE user_consents ADD COLUMN revoked_at TIMESTAMP WITH TIME ZONE NULL;"))
            print("Successfully added revoked_at column.")
        else:
            print("revoked_at already exists.")

        # 3. Add metadata_json if missing
        if "metadata_json" not in columns:
            print("Adding metadata_json column...")
            conn.execute(text("ALTER TABLE user_consents ADD COLUMN metadata_json JSONB DEFAULT '{}'::jsonb;"))
            print("Successfully added metadata_json column.")
        else:
            print("metadata_json already exists.")

        conn.commit()

if __name__ == "__main__":
    run_migration()
