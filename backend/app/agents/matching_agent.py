"""
Matching Agent — scores and ranks jobs against candidate profiles.
Identifies skill gaps and calls Skill Lab integrations for course recommendations.
"""
import logging
from sqlalchemy.orm import Session
from app.models.models import Candidate, Job, JobMatch
from app.mcp.servers import VectorServer, SkillLabServer

logger = logging.getLogger("app.agents.matching")


class MatchingAgent:
    
    def score_job(self, candidate_id: int, job_id: int, db: Session) -> float:
        """Calculates multi-dimensional match score between a candidate and a job."""
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not candidate or not job:
            logger.error(f"Cannot score: Candidate ({candidate_id}) or Job ({job_id}) not found")
            return 0.0
            
        # 1. Skills Match (40% weight - via vector similarity)
        cand_skills = candidate.skills or ""
        job_skills = job.required_skills or ""
        
        vector_server = VectorServer()
        cand_vec = vector_server.embed_text(candidate.user_id, {"text": cand_skills}, db)["embedding"]
        job_vec = vector_server.embed_text(candidate.user_id, {"text": job_skills}, db)["embedding"]
        
        from app.mcp.servers import cosine_similarity
        skill_score = round(cosine_similarity(cand_vec, job_vec) * 100.0)
        
        # 2. Experience Match (20% weight)
        exp_score = 100.0
        # Simple heuristic check: if junior / senior keyword match
        if job.experience_level.lower() == "senior" and (candidate.status or "").lower() == "registered":
            exp_score = 50.0  # Lower score if senior job and junior candidate
            
        # 3. Education Match (10% weight)
        edu_score = 100.0
        
        # 4. Location Match (10% weight)
        loc_score = 100.0
        cand_loc = (candidate.address or "").lower()
        job_loc = job.location.lower()
        if "remote" in job_loc:
            loc_score = 100.0
        elif cand_loc and cand_loc not in job_loc:
            loc_score = 30.0  # Mismatch in physical locations
            
        # 5. Project/Certification Match (10% weight)
        proj_score = 80.0
        
        # 6. Title Semantic Match (10% weight)
        title_vec = vector_server.embed_text(candidate.user_id, {"text": job.title}, db)["embedding"]
        summary_vec = vector_server.embed_text(candidate.user_id, {"text": candidate.summary or job.title}, db)["embedding"]
        title_score = round(cosine_similarity(title_vec, summary_vec) * 100.0)

        # Combined Match Score
        match_score = (
            (skill_score * 0.40) +
            (exp_score * 0.20) +
            (edu_score * 0.10) +
            (loc_score * 0.10) +
            (proj_score * 0.10) +
            (title_score * 0.10)
        )
        
        # Identify missing skills (Simple subtraction)
        cand_skills_set = {s.strip().lower() for s in cand_skills.split(",") if s.strip()}
        job_skills_list = [s.strip() for s in job_skills.split(",") if s.strip()]
        missing_skills = [s for s in job_skills_list if s.lower() not in cand_skills_set]
        
        # Update or Save JobMatch table
        match_record = db.query(JobMatch).filter(
            JobMatch.candidate_id == candidate_id,
            JobMatch.job_id == job_id
        ).first()
        
        if not match_record:
            match_record = JobMatch(
                candidate_id=candidate_id,
                job_id=job_id,
                skill_match=skill_score,
                experience_match=exp_score,
                education_match=edu_score,
                location_match=loc_score,
                project_match=proj_score,
                match_score=match_score,
                skills_gap=", ".join(missing_skills)
            )
            db.add(match_record)
        else:
            match_record.skill_match = skill_score
            match_record.experience_match = exp_score
            match_record.education_match = edu_score
            match_record.location_match = loc_score
            match_record.project_match = proj_score
            match_record.match_score = match_score
            match_record.skills_gap = ", ".join(missing_skills)
            
        db.commit()
        
        # Trigger Skill Lab Course recommendation if score is below 95% and missing skills exist
        if match_score < 95.0 and missing_skills:
            try:
                SkillLabServer().create_learning_path(
                    user_id=candidate.user_id,
                    arguments={"skills": missing_skills},
                    db=db
                )
                logger.info(f"Triggered Skill Lab recommendations for missing skills: {missing_skills}")
            except Exception as e:
                logger.error(f"Failed to trigger Skill Lab path matching: {e}")
                
        return match_score
