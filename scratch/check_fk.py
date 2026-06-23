import os
import sys
from dotenv import load_dotenv
import psycopg2

# Add backend directory to path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
load_dotenv()
root_env = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env")
if os.path.exists(root_env):
    load_dotenv(root_env)

from app.core.config import settings

def check_dependencies():
    conn = psycopg2.connect(settings.DATABASE_URL)
    cur = conn.cursor()
    
    # Query to fetch all foreign key constraints, their source tables, columns, target tables, and columns
    cur.execute("""
        SELECT
            tc.table_schema, 
            tc.table_name, 
            kcu.column_name, 
            ccu.table_schema AS foreign_table_schema,
            ccu.table_name AS foreign_table_name,
            ccu.column_name AS foreign_column_name,
            tc.constraint_name
        FROM 
            information_schema.table_constraints AS tc 
            JOIN information_schema.key_column_usage AS kcu
              ON tc.constraint_name = kcu.constraint_name
              AND tc.table_schema = kcu.table_schema
            JOIN information_schema.constraint_column_usage AS ccu
              ON ccu.constraint_name = tc.constraint_name
              AND ccu.table_schema = tc.table_schema
        WHERE tc.constraint_type = 'FOREIGN KEY'
        ORDER BY tc.table_schema, tc.table_name;
    """)
    constraints = cur.fetchall()
    
    print("--- FOREIGN KEY CONSTRAINTS IN DB ---")
    for row in constraints:
        print(f"Table '{row[0]}.{row[1]}' column '{row[2]}' REFERENCES '{row[3]}.{row[4]}' column '{row[5]}' (Constraint: {row[6]})")
        
    cur.close()
    conn.close()

if __name__ == "__main__":
    check_dependencies()
