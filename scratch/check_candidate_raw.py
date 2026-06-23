import json
from sqlalchemy import create_engine, text

DATABASE_URL = "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@thomas.proxy.rlwy.net:20637/Vidyamargai"
engine = create_engine(DATABASE_URL)

def run():
    out = []
    with engine.connect() as conn:
        user = conn.execute(text("SELECT * FROM users WHERE email = 'j.shivachary@gmail.com'")).fetchone()
        if not user:
            out.append("User j.shivachary@gmail.com not found")
        else:
            user_dict = dict(user._mapping)
            out.append(f"USER: {user_dict['id']} | {user_dict['full_name']} | {user_dict['email']}")
            
            candidate = conn.execute(text(f"SELECT * FROM candidates WHERE user_id = {user_dict['id']}")).fetchone()
            if not candidate:
                out.append("CANDIDATE not found")
            else:
                cand_dict = dict(candidate._mapping)
                out.append("CANDIDATE details:")
                for k, v in cand_dict.items():
                    out.append(f"  - {k}: {v}")
                    
                resumes = conn.execute(text(f"SELECT * FROM candidate_resumes WHERE candidate_id = {cand_dict['id']} ORDER BY uploaded_at DESC")).fetchall()
                out.append(f"RESUMES ({len(resumes)}):")
                for r in resumes:
                    r_dict = dict(r._mapping)
                    out.append(f"  - ID: {r_dict['id']} | URL: {r_dict['resume_url']} | Active: {r_dict.get('is_active')} | Uploaded: {r_dict['uploaded_at']}")
                    
                profiles = conn.execute(text(f"SELECT * FROM candidate_profiles WHERE candidate_id = {cand_dict['id']} ORDER BY created_at DESC")).fetchall()
                out.append(f"PROFILES ({len(profiles)}):")
                for p in profiles:
                    p_dict = dict(p._mapping)
                    out.append(f"  - ID: {p_dict['id']} | Resume ID: {p_dict.get('resume_id')} | Created: {p_dict['created_at']}")
                    out.append(f"    Skills Graph: {p_dict.get('skills_graph')}")
                    out.append(f"    Parsed Metadata: {p_dict.get('parsed_metadata')}")
                    
    with open("scratch/candidate_data.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(out))
    print("Done")

if __name__ == "__main__":
    run()
