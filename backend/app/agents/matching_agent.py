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
from app.services.job_connectors.base import get_canonical_domain

logger = logging.getLogger("app.agents.matching")


def calculate_match_score_and_reasons(
    profile, 
    job_title: str, 
    job_description: str, 
    job_skills_list, 
    job_experience_str: str
) -> dict:
    import re
    
    # Normalize job_skills_list
    if not job_skills_list:
        job_skills_list = []
    elif isinstance(job_skills_list, str):
        job_skills_list = [s.strip() for s in job_skills_list.split(",") if s.strip()]
    elif not isinstance(job_skills_list, list):
        job_skills_list = list(job_skills_list)
        
    # 0. Parsing helpers & Rejection Flags
    cand_domain = getattr(profile, "domain", "Other") or "Other"
    cand_years = getattr(profile, "experience_years", 0.0) or 0.0
    cand_skills = {s.lower().strip() for s in (profile.skills or [])}
    
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
    
    # Pre-scoring Rejections
    # Rejection 1: Domain mismatch (reject if domains differ and are known)
    cand_canonical = get_canonical_domain(cand_domain)
    job_canonical = get_canonical_domain(job_title)
    domain_mismatch = False
    if cand_canonical != "other" and job_canonical != "other" and cand_canonical != job_canonical:
        domain_mismatch = True
        
    # Rejection 2: Experience gap > 5 years
    experience_gap = req_years - cand_years
    
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
                
    # Rejection 3: Skill overlap < 10%
    total_skills_count = len(job_skills_list) if job_skills_list else 5
    matched_skills_count = len(matched_skills) if job_skills_list else 0
    
    # Check description text if no skill list is provided
    desc_lower = (job_description or "").lower()
    hits_list = []
    if not job_skills_list:
        for cs in cand_skills:
            if cs in desc_lower:
                hits_list.append(cs)
        matched_skills_count = len(hits_list)
        
    overlap_pct = (matched_skills_count / total_skills_count) if job_skills_list else (matched_skills_count / max(1, len(cand_skills)))
    
    if domain_mismatch or (experience_gap > 5) or (overlap_pct < 0.10):
        # Reject job match
        reasons = []
        if domain_mismatch:
            reasons.append(f"Rejected: Domain mismatch (Candidate: '{cand_canonical}', Job: '{job_canonical}').")
        if experience_gap > 5:
            reasons.append(f"Rejected: Experience gap too large (Required: {req_years} yrs, Candidate has: {cand_years} yrs).")
        if overlap_pct < 0.10:
            reasons.append(f"Rejected: Skill overlap is too low ({int(overlap_pct * 100)}% matched).")
            
        return {
            "match_score": 0.0,
            "role_score": 0.0,
            "skills_score": 0.0,
            "exp_score": 0.0,
            "edu_score": 0.0,
            "cert_score": 0.0,
            "matched_skills": [],
            "missing_skills": job_skills_list or [],
            "reasons": reasons,
            "rejected": True
        }

    # 1. Domain/Role Match (30%)
    role_score = 40.0
    reasons = []
    t = (job_title or "").lower()
    pref_roles = [r.lower().strip() for r in (profile.preferred_roles or [])]
    
    role_matched = False
    for r in pref_roles:
        if r in t or t in r:
            role_score = 100.0
            reasons.append(f"Strong role match: Your preferred role '{r}' aligns with job title '{job_title}'.")
            role_matched = True
            break
            
    if not role_matched:
        if cand_canonical != "other" and job_canonical != "other" and cand_canonical == job_canonical:
            role_score = 85.0
            reasons.append(f"Domain match: Job title aligns with your domain '{profile.domain}'.")
        else:
            role_score = 40.0
            reasons.append("Partial role match based on general engineering/technical alignment.")

    # 2. Skill Match (30%) - Weighted: 0.7 for first 3 (required), 0.3 for optional
    if job_skills_list:
        num_req = min(3, len(job_skills_list))
        required_skills = job_skills_list[:num_req]
        optional_skills = job_skills_list[num_req:]
        
        req_matched = [s for s in required_skills if any(s.strip().lower() in cs or cs in s.strip().lower() for cs in cand_skills)]
        opt_matched = [s for s in optional_skills if any(s.strip().lower() in cs or cs in s.strip().lower() for cs in cand_skills)]
        
        req_score = (len(req_matched) / len(required_skills)) * 100.0 if required_skills else 100.0
        opt_score = (len(opt_matched) / len(optional_skills)) * 100.0 if optional_skills else 100.0
        
        skill_score = (req_score * 0.7) + (opt_score * 0.3)
        reasons.append(f"Skills match: {len(matched_skills)}/{len(job_skills_list)} skills matched ({int(skill_score)}% weighted score).")
    else:
        # Check description
        if len(hits_list) >= 4:
            skill_score = 90.0
            reasons.append(f"Skills match: Several profile skills ({', '.join(hits_list[:4])}) found in job description.")
        elif len(hits_list) >= 2:
            skill_score = 75.0
            reasons.append(f"Skills match: Some profile skills ({', '.join(hits_list[:2])}) found in job description.")
        else:
            skill_score = 50.0
            reasons.append("Skills match: Limited overlap found between profile skills and job description.")

    # 3. Experience Match (15%)
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

    # 4. Semantic Similarity (15%) - fast keyword-based semantic overlap in title + description
    title_lower = (job_title or "").lower()
    keywords = set()
    for s in (profile.skills or []):
        keywords.add(s.lower().strip())
    for r in (profile.preferred_roles or []):
        keywords.update(r.lower().split())
    keywords = {kw for kw in keywords if len(kw) > 2}
    
    hits = 0
    for kw in keywords:
        if kw in title_lower:
            hits += 3
        elif kw in desc_lower:
            hits += 1
            
    semantic_score = min(100.0, (hits / max(1, len(keywords) // 2)) * 100.0) if keywords else 100.0
    reasons.append(f"Semantic similarity: Alignment score of {int(semantic_score)}% between candidate profile and job context.")

    # 5. Education & Certifications Match (10%)
    edu_score = 100.0
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

    edu_cert_score = (edu_score * 0.6) + (cert_score * 0.4)

    # Combined Match Score (sums to 100%)
    match_score = (
        (role_score * 0.30) +
        (skill_score * 0.30) +
        (exp_score * 0.15) +
        (semantic_score * 0.15) +
        (edu_cert_score * 0.10)
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
        "reasons": reasons,
        "rejected": False
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
        
        # Enforce minimum threshold of 60 or early rejection flag
        if res.get("rejected") or match_score < 60.0:
            match_record = db.query(JobMatch).filter(
                JobMatch.candidate_id == candidate_id,
                JobMatch.job_id == job_id
            ).first()
            if match_record:
                db.delete(match_record)
                db.commit()
            logger.info(f"Job {job_id} match score ({match_score}) below 60.0 threshold or rejected. Rejecting.")
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
