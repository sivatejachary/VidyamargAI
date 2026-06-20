"""
Matching Agent — scores and ranks jobs against candidate profiles.
Identifies skill gaps and calls Skill Lab integrations for course recommendations.
"""
import re
import json
import logging
from sqlalchemy.orm import Session
from app.models.models import Candidate, Job, JobMatch
from app.agents.resume_intelligence import ResumeIntelligenceAgent

logger = logging.getLogger("app.agents.matching")


def calculate_match_score_and_reasons(
    profile, 
    job_title: str, 
    job_description: str, 
    job_skills_list: list, 
    job_experience_str: str
) -> dict:
    import re
    
    # 1. Role Match (40%)
    role_score = 40.0
    reasons = []
    
    t = (job_title or "").lower()
    pref_roles = [r.lower().strip() for r in (profile.preferred_roles or [])]
    cand_domain = (profile.domain or "").lower()
    
    role_matched = False
    for r in pref_roles:
        if r in t or t in r:
            role_score = 100.0
            reasons.append(f"Strong role match: Your preferred role '{r}' aligns with job title '{job_title}'.")
            role_matched = True
            break
            
    if not role_matched:
        if cand_domain and (cand_domain in t or any(kw in t for kw in ["software", "developer", "engineer"] if cand_domain == "software engineering")):
            role_score = 85.0
            reasons.append(f"Domain match: Job title aligns with your domain '{profile.domain}'.")
        else:
            role_score = 40.0
            reasons.append("Partial role match based on general engineering/technical alignment.")

    # 2. Skill Match (25%)
    cand_skills = {s.lower().strip() for s in (profile.skills or [])}
    
    # Clean job skills
    matched_skills = []
    missing_skills = []
    
    if job_skills_list:
        for js in job_skills_list:
            js_clean = js.strip().lower()
            if not js_clean:
                continue
            if any(js_clean in cs or cs in js_clean for cs in cand_skills):
                matched_skills.append(js.strip())
            else:
                missing_skills.append(js.strip())
        skill_score = (len(matched_skills) / len(job_skills_list)) * 100.0
        reasons.append(f"Skills match: {len(matched_skills)}/{len(job_skills_list)} required skills matched ({int(skill_score)}%).")
    else:
        # Check description
        desc_lower = (job_description or "").lower()
        hits = []
        for cs in cand_skills:
            if cs in desc_lower:
                hits.append(cs)
        if len(hits) >= 4:
            skill_score = 90.0
            reasons.append(f"Skills match: Several profile skills ({', '.join(hits[:4])}) found in job description.")
        elif len(hits) >= 2:
            skill_score = 75.0
            reasons.append(f"Skills match: Some profile skills ({', '.join(hits[:2])}) found in job description.")
        else:
            skill_score = 50.0
            reasons.append("Skills match: Limited overlap found between profile skills and job description.")

    # 3. Experience Match (20%)
    def get_required_years(exp_str: str) -> int:
        if not exp_str:
            return 0
        exp_str = exp_str.lower()
        if "fresher" in exp_str or "intern" in exp_str or "0-" in exp_str:
            return 0
        match = re.search(r'(\d+)\s*(?:-|to)?\s*(?:\d+)?\s*year', exp_str)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)\s*\+', exp_str)
        if match:
            return int(match.group(1))
        match = re.search(r'(\d+)', exp_str)
        if match:
            return int(match.group(1))
        return 0

    req_years = get_required_years(job_experience_str)
    cand_years = profile.experience_years
    
    if req_years == 0:
        if cand_years <= 2.0:
            exp_score = 100.0
            reasons.append(f"Experience match: Perfect fit for a junior/fresher role (You have {cand_years} years).")
        else:
            exp_score = 80.0
            reasons.append(f"Experience match: Slightly overqualified for this junior role (Required: 0 years, You have {cand_years} years).")
    else:
        diff = cand_years - req_years
        if diff >= 0:
            exp_score = 100.0
            reasons.append(f"Experience match: You exceed the required experience of {req_years} years (You have {cand_years} years).")
        elif diff == -1.0:
            exp_score = 75.0
            reasons.append(f"Experience match: Almost matches required experience of {req_years} years (You have {cand_years} years).")
        elif diff == -2.0:
            exp_score = 50.0
            reasons.append(f"Experience match: Partially matches required experience of {req_years} years (You have {cand_years} years).")
        else:
            exp_score = 25.0
            reasons.append(f"Experience match: Below required experience of {req_years} years (You have {cand_years} years).")

    # 4. Education Match (10%)
    edu_score = 100.0
    desc_lower = (job_description or "").lower()
    edu_terms = ["degree", "bachelor", "btech", "mtech", "mba", "mca", "bca", "graduate", "diploma", "ca "]
    specifies_edu = any(t in desc_lower for t in edu_terms)
    
    if specifies_edu:
        cand_edu = (profile.education or "").lower()
        if any(t in cand_edu for t in ["b.tech", "btech", "b.e", "bachelor", "m.tech", "mtech", "master", "mca", "ca ", "mba"]):
            edu_score = 100.0
            reasons.append("Education match: Your degree aligns with the educational requirements of this role.")
        else:
            edu_score = 60.0
            reasons.append("Education match: Mismatch between your degree and required educational qualifications.")
    else:
        edu_score = 100.0
        reasons.append("Education match: No specific educational constraints specified for this role.")

    # 5. Certification Match (5%)
    cert_score = 100.0
    if any(t in desc_lower for t in ["certificat", "license", "credential"]):
        if profile.certifications:
            cert_score = 100.0
            reasons.append("Certification match: Your profile certifications align with job preferences.")
        else:
            cert_score = 30.0
            reasons.append("Certification match: Role lists certifications as preferred/required, but none found on your profile.")
    else:
        cert_score = 100.0
        reasons.append("Certification match: No certification requirements listed for this role.")

    # Combined Match Score
    match_score = (
        (role_score * 0.40) +
        (skill_score * 0.25) +
        (exp_score * 0.20) +
        (edu_score * 0.10) +
        (cert_score * 0.05)
    )
    match_score = round(match_score, 1)

    return {
        "match_score": match_score,
        "role_score": role_score,
        "skills_score": skill_score,
        "exp_score": exp_score,
        "edu_score": edu_score,
        "cert_score": cert_score,
        "matched_skills": matched_skills,
        "missing_skills": missing_skills,
        "reasons": reasons
    }


class MatchingAgent:
    
    def score_job(self, candidate_id: int, job_id: int, db: Session) -> float:
        """Calculates multi-dimensional match score between a candidate and a job."""
        candidate = db.query(Candidate).filter(Candidate.id == candidate_id).first()
        job = db.query(Job).filter(Job.id == job_id).first()
        
        if not candidate or not job:
            logger.error(f"Cannot score: Candidate ({candidate_id}) or Job ({job_id}) not found")
            return 0.0
            
        profile = ResumeIntelligenceAgent(db, candidate_id).extract_profile()
        
        # Split required skills
        job_skills_list = [s.strip() for s in (job.required_skills or "").split(",") if s.strip()]
        
        res = calculate_match_score_and_reasons(
            profile=profile,
            job_title=job.title,
            job_description=job.description,
            job_skills_list=job_skills_list,
            job_experience_str=job.experience_level
        )
        
        match_score = res["match_score"]
        
        # Enforce minimum threshold of 60
        if match_score < 60.0:
            match_record = db.query(JobMatch).filter(
                JobMatch.candidate_id == candidate_id,
                JobMatch.job_id == job_id
            ).first()
            if match_record:
                db.delete(match_record)
                db.commit()
            logger.info(f"Job {job_id} match score ({match_score}) below 60.0 threshold. Rejecting.")
            return 0.0
            
        # Update or Save JobMatch table
        match_record = db.query(JobMatch).filter(
            JobMatch.candidate_id == candidate_id,
            JobMatch.job_id == job_id
        ).first()
        
        if not match_record:
            match_record = JobMatch(
                candidate_id=candidate_id,
                job_id=job_id,
                skill_match=res["skills_score"],
                experience_match=res["exp_score"],
                education_match=res["edu_score"],
                location_match=res["role_score"],  # Map role score here
                project_match=res["cert_score"],    # Map cert score here
                match_score=match_score,
                skills_gap=", ".join(res["missing_skills"]),
                reasons_json=res["reasons"]
            )
            db.add(match_record)
        else:
            match_record.skill_match = res["skills_score"]
            match_record.experience_match = res["exp_score"]
            match_record.education_match = res["edu_score"]
            match_record.location_match = res["role_score"]
            match_record.project_match = res["cert_score"]
            match_record.match_score = match_score
            match_record.skills_gap = ", ".join(res["missing_skills"])
            match_record.reasons_json = res["reasons"]
            
        db.commit()
        
        # Trigger Skill Lab Course recommendation if score is below 95% and missing skills exist
        if match_score < 95.0 and res["missing_skills"]:
            try:
                from app.mcp.servers import SkillLabServer
                SkillLabServer().create_learning_path(
                    user_id=candidate.user_id,
                    arguments={"skills": res["missing_skills"]},
                    db=db
                )
                logger.info(f"Triggered Skill Lab recommendations for missing skills: {res['missing_skills']}")
            except Exception as e:
                logger.error(f"Failed to trigger Skill Lab path matching: {e}")
                
        return match_score
