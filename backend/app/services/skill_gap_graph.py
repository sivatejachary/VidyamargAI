"""
Skill Gap Graph — maps skills to job impact and learning paths.
High-value feature: shows candidates what learning unlocks what jobs.
"""
import logging
from dataclasses import dataclass, field
from typing import Optional
from sqlalchemy.orm import Session

logger = logging.getLogger("app.services.skill_gap_graph")


@dataclass
class SkillImpact:
    skill: str
    jobs_unlocked: int
    child_skills: list
    recommended_course_id: Optional[str] = None
    recommended_course_title: Optional[str] = None


@dataclass
class LearningStep:
    step_number: int
    skill: str
    course_id: Optional[str]
    course_title: Optional[str]
    jobs_unlocked: int
    estimated_hours: int = 20


# Static skill tree — fast, no DB queries needed
SKILL_TREE: dict = {
    "Python": {
        "children": ["NumPy", "Pandas", "FastAPI", "Scikit-learn", "TensorFlow", "Django"],
        "unlocks_job_titles": ["Data Scientist", "Backend Engineer", "ML Engineer", "Data Analyst"],
        "avg_jobs_unlocked": 234,
        "estimated_hours": 40,
    },
    "React": {
        "children": ["Redux", "Next.js", "TypeScript", "React Native", "GraphQL"],
        "unlocks_job_titles": ["Frontend Engineer", "Full Stack Developer", "React Developer"],
        "avg_jobs_unlocked": 187,
        "estimated_hours": 35,
    },
    "Next.js": {
        "children": ["TypeScript", "Vercel", "React"],
        "unlocks_job_titles": ["Full Stack Developer", "Frontend Engineer"],
        "avg_jobs_unlocked": 142,
        "estimated_hours": 25,
    },
    "TypeScript": {
        "children": ["React", "Node.js", "Angular"],
        "unlocks_job_titles": ["Frontend Engineer", "Full Stack Developer"],
        "avg_jobs_unlocked": 165,
        "estimated_hours": 20,
    },
    "AWS": {
        "children": ["EC2", "S3", "Lambda", "ECS", "RDS", "CloudFormation"],
        "unlocks_job_titles": ["Cloud Engineer", "DevOps Engineer", "SRE", "Platform Engineer"],
        "avg_jobs_unlocked": 312,
        "estimated_hours": 60,
    },
    "Docker": {
        "children": ["Kubernetes", "Docker Compose", "Container Security"],
        "unlocks_job_titles": ["DevOps Engineer", "Platform Engineer", "Backend Engineer"],
        "avg_jobs_unlocked": 156,
        "estimated_hours": 25,
    },
    "Kubernetes": {
        "children": ["Helm", "Istio", "AWS EKS"],
        "unlocks_job_titles": ["DevOps Engineer", "SRE", "Platform Engineer"],
        "avg_jobs_unlocked": 198,
        "estimated_hours": 40,
    },
    "Machine Learning": {
        "children": ["TensorFlow", "PyTorch", "Scikit-learn", "MLflow"],
        "unlocks_job_titles": ["ML Engineer", "Data Scientist", "AI Engineer"],
        "avg_jobs_unlocked": 178,
        "estimated_hours": 50,
    },
    "TensorFlow": {
        "children": ["Keras", "TFX", "TensorFlow Lite"],
        "unlocks_job_titles": ["ML Engineer", "Deep Learning Engineer"],
        "avg_jobs_unlocked": 134,
        "estimated_hours": 35,
    },
    "SQL": {
        "children": ["PostgreSQL", "MySQL", "SQLite", "BigQuery"],
        "unlocks_job_titles": ["Backend Engineer", "Data Analyst", "Data Engineer"],
        "avg_jobs_unlocked": 245,
        "estimated_hours": 20,
    },
    "Node.js": {
        "children": ["Express.js", "NestJS", "GraphQL", "Socket.io"],
        "unlocks_job_titles": ["Backend Engineer", "Full Stack Developer"],
        "avg_jobs_unlocked": 189,
        "estimated_hours": 30,
    },
    "Java": {
        "children": ["Spring Boot", "Hibernate", "Maven", "Microservices"],
        "unlocks_job_titles": ["Backend Engineer", "Java Developer", "Software Engineer"],
        "avg_jobs_unlocked": 221,
        "estimated_hours": 50,
    },
}

# Normalize keys for case-insensitive lookup
_SKILL_TREE_LOWER = {k.lower(): (k, v) for k, v in SKILL_TREE.items()}


def find_matching_course(skill: str, db: Session) -> tuple:
    """Finds the best matching course from DB for a given skill."""
    try:
        from sqlalchemy import text
        skill_lower = skill.lower()
        result = db.execute(
            text("SELECT id, title FROM courses WHERE LOWER(title) LIKE :skill ORDER BY id LIMIT 1"),
            {"skill": f"%{skill_lower}%"}
        ).first()
        if result:
            return (str(result[0]), result[1])
    except Exception as e:
        logger.debug(f"Course lookup for '{skill}': {e}")
    return (None, None)


def get_skill_impact(skill: str, db: Session = None, actual_job_count: int = None) -> SkillImpact:
    """Returns job impact and children for a skill."""
    key, node = _SKILL_TREE_LOWER.get(skill.lower(), (skill, {}))
    course_id, course_title = (None, None)
    if db:
        course_id, course_title = find_matching_course(skill, db)
    return SkillImpact(
        skill=key,
        jobs_unlocked=actual_job_count or node.get("avg_jobs_unlocked", 50),
        child_skills=node.get("children", []),
        recommended_course_id=course_id,
        recommended_course_title=course_title,
    )


def get_learning_path(missing_skills: list, db: Session = None) -> list:
    """Returns ordered learning steps prioritized by job impact."""
    steps = []
    sorted_skills = sorted(
        missing_skills,
        key=lambda s: _SKILL_TREE_LOWER.get(s.lower(), (s, {}))[1].get("avg_jobs_unlocked", 50),
        reverse=True
    )
    for i, skill in enumerate(sorted_skills[:6], 1):
        key, node = _SKILL_TREE_LOWER.get(skill.lower(), (skill, {}))
        course_id, course_title = (None, None)
        if db:
            course_id, course_title = find_matching_course(skill, db)
        steps.append(LearningStep(
            step_number=i,
            skill=key,
            course_id=course_id,
            course_title=course_title or f"{key} Fundamentals",
            jobs_unlocked=node.get("avg_jobs_unlocked", 50),
            estimated_hours=node.get("estimated_hours", 20),
        ))
    return steps
