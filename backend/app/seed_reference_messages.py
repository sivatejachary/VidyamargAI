import sqlite3
from datetime import datetime

def seed():
    conn = sqlite3.connect('hireai.db')
    cursor = conn.cursor()
    
    # 1. Update Candidate 1 details
    cursor.execute("""
        UPDATE candidates 
        SET hackathon_team = NULL,
            assigned_mentor = NULL,
            hackathon_problem = NULL,
            hackathon_members = NULL
        WHERE id = 1
    """)
    
    # 2. Insert Jobs (Microsoft & Amazon) if they don't exist
    cursor.execute("DELETE FROM jobs WHERE id IN (1, 2)")
    cursor.execute("""
        INSERT INTO jobs (id, title, description, required_skills, experience_level, salary_range, location, department, status)
        VALUES 
        (1, 'Microsoft', 'Software Engineer', 'C#', 'Senior', '$150k', 'Redmond, WA', 'Engineering', 'active'),
        (2, 'Amazon', 'Software Development Engineer', 'Java', 'Senior', '$160k', 'Seattle, WA', 'Engineering', 'active')
    """)
    
    # 3. Clear all applications and messages to remove dummy data
    cursor.execute("DELETE FROM applications")
    cursor.execute("DELETE FROM messages")
    
    conn.commit()
    conn.close()
    print("Database successfully cleared of dummy applications and messages!")

if __name__ == '__main__':
    seed()
