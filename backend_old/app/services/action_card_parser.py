"""
Action Card Parser — converts AI text responses into structured UI cards.
The AI suggests things; this service finds the real DB objects.
"""
import re
import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.schemas.mcp_schemas import ActionCard

logger = logging.getLogger("app.services.action_card_parser")

# Patterns to detect course recommendations in AI text
COURSE_PATTERNS = [
    r"learn\s+([\w\s\.\+]+?)(?:\s+course|\s+fundamentals|\s+basics|\.|,|$)",
    r"take\s+(?:the\s+)?([\w\s\.\+]+?)\s+course",
    r"study\s+([\w\s\.\+]+?)(?:\.|,|$)",
    r"enroll\s+in\s+([\w\s\.\+]+?)(?:\.|,|$)",
    r"complete\s+(?:the\s+)?([\w\s\.\+]+?)\s+course",
    r"recommend\s+([\w\s\.\+]+?)\s+(?:course|training|tutorial)",
]

# Patterns to detect job recommendations
JOB_PATTERNS = [
    r"apply\s+(?:to\s+|for\s+)?(.+?)\s+(?:at|@)\s+(.+?)(?:\.|,|$)",
    r"([\w\s]+?)\s+role\s+at\s+(.+?)(?:\.|,|$)",
    r"([\w\s]+?)\s+position\s+at\s+(.+?)(?:\.|,|$)",
]

STOP_WORDS = {"the", "a", "an", "this", "that", "your", "our", "their"}


def _clean_skill(text: str) -> str:
    words = text.strip().split()
    words = [w for w in words if w.lower() not in STOP_WORDS]
    return " ".join(words[:3]).strip()


def _find_closest_course(skill: str, db: Session) -> Optional[dict]:
    """Fuzzy-finds the closest matching course in the DB."""
    try:
        from sqlalchemy import text
        skill_clean = skill.strip().lower()
        # Exact title match first
        result = db.execute(
            text("SELECT id, title FROM courses WHERE LOWER(title) LIKE :s ORDER BY LENGTH(title) ASC LIMIT 1"),
            {"s": f"%{skill_clean}%"}
        ).first()
        if result:
            return {"id": str(result[0]), "title": result[1]}
    except Exception as e:
        logger.debug(f"Course lookup: {e}")
    return None


def _find_closest_job(title: str, company: str, db: Session) -> Optional[dict]:
    """Finds the closest matching active job in the DB."""
    try:
        from sqlalchemy import text
        result = db.execute(
            text("""
                SELECT id, title, department, salary_range
                FROM jobs WHERE status = 'active'
                AND (LOWER(title) LIKE :title OR LOWER(department) LIKE :company)
                LIMIT 1
            """),
            {"title": f"%{title.strip().lower()[:20]}%", "company": f"%{company.strip().lower()[:20]}%"}
        ).first()
        if result:
            return {"id": result[0], "title": result[1], "company": result[2], "salary": result[3] or ""}
    except Exception as e:
        logger.debug(f"Job lookup: {e}")
    return None


def parse_action_cards(
    response: str,
    db: Session,
    candidate_id: int,
    mode: str = "general"
) -> list[ActionCard]:
    """Scans AI response text and builds a list of actionable UI cards."""
    cards = []
    seen_ids = set()

    # --- Course cards ---
    for pattern in COURSE_PATTERNS:
        for match in re.finditer(pattern, response, re.IGNORECASE):
            raw_skill = _clean_skill(match.group(1))
            if len(raw_skill) < 2 or raw_skill.lower() in seen_ids:
                continue
            course = _find_closest_course(raw_skill, db)
            if course and course["id"] not in seen_ids:
                seen_ids.add(course["id"])
                # Try to get job impact from skill graph
                jobs_count = 50
                try:
                    from app.services.skill_gap_graph import get_skill_impact
                    impact = get_skill_impact(raw_skill)
                    jobs_count = impact.jobs_unlocked
                except Exception:
                    pass
                cards.append(ActionCard(
                    type="course",
                    id=course["id"],
                    title=course["title"],
                    subtitle=f"Learn this → Unlock ~{jobs_count} jobs",
                    action_label="Start Learning",
                    action_href=f"/candidate/skill-lab?course={course['id']}",
                    meta={"skill": raw_skill, "jobs_unlocked": jobs_count}
                ))
                if len(cards) >= 2:
                    break
        if len(cards) >= 4:
            break

    # --- Job cards ---
    if mode in ["job-agent", "general"]:
        for pattern in JOB_PATTERNS:
            for match in re.finditer(pattern, response, re.IGNORECASE):
                title = match.group(1).strip()
                company = match.group(2).strip() if len(match.groups()) > 1 else ""
                job = _find_closest_job(title, company, db)
                if job and str(job["id"]) not in seen_ids:
                    seen_ids.add(str(job["id"]))
                    cards.append(ActionCard(
                        type="job",
                        id=job["id"],
                        title=f"{job['title']}",
                        subtitle=f"{job['company']} · {job['salary'] or 'Competitive'}",
                        action_label="View Job",
                        action_href=f"/candidate/jobs?job={job['id']}",
                        meta={"company": job["company"]}
                    ))
                    if len(cards) >= 4:
                        break

    return cards[:4]
