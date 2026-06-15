"""
AI-powered search query generator.
Converts resume skills into effective job search queries
that return relevant Indian job listings.
"""
from typing import List
import logging

logger = logging.getLogger(__name__)


# Maps raw skills to better job role terms
SKILL_TO_ROLE = {
    "python": ["Python Developer", "Backend Developer", "Software Engineer"],
    "fastapi": ["FastAPI Developer", "Backend Engineer", "Python Backend Developer"],
    "django": ["Django Developer", "Python Web Developer", "Backend Developer"],
    "flask": ["Flask Developer", "Python Developer", "Backend Engineer"],
    "react": ["React Developer", "Frontend Developer", "Full Stack Developer"],
    "nextjs": ["Next.js Developer", "React Developer", "Full Stack Engineer"],
    "next.js": ["Next.js Developer", "React Developer", "Full Stack Engineer"],
    "javascript": ["JavaScript Developer", "Frontend Developer", "Full Stack Developer"],
    "typescript": ["TypeScript Developer", "Frontend Engineer", "Full Stack Developer"],
    "nodejs": ["Node.js Developer", "Backend Developer", "Full Stack Engineer"],
    "node.js": ["Node.js Developer", "Backend Developer", "Full Stack Engineer"],
    "vue": ["Vue.js Developer", "Frontend Developer", "JavaScript Engineer"],
    "angular": ["Angular Developer", "Frontend Developer", "JavaScript Engineer"],
    "java": ["Java Developer", "Backend Engineer", "Software Engineer"],
    "spring": ["Spring Boot Developer", "Java Backend Developer", "Microservices Engineer"],
    "kotlin": ["Kotlin Developer", "Android Developer", "Mobile Developer"],
    "flutter": ["Flutter Developer", "Mobile Developer", "Cross-Platform Developer"],
    "dart": ["Flutter Developer", "Dart Developer", "Mobile Engineer"],
    "android": ["Android Developer", "Mobile Developer", "Kotlin Developer"],
    "ios": ["iOS Developer", "Swift Developer", "Mobile Developer"],
    "swift": ["iOS Developer", "Swift Developer", "Apple Developer"],
    "machine learning": ["ML Engineer", "Machine Learning Engineer", "AI Engineer"],
    "deep learning": ["Deep Learning Engineer", "AI/ML Engineer", "Computer Vision Engineer"],
    "tensorflow": ["ML Engineer", "Deep Learning Engineer", "AI Developer"],
    "pytorch": ["PyTorch Developer", "Deep Learning Engineer", "AI Researcher"],
    "nlp": ["NLP Engineer", "AI Engineer", "Data Scientist"],
    "llm": ["LLM Engineer", "Generative AI Developer", "AI Engineer"],
    "rag": ["AI Engineer", "LLM Developer", "Generative AI Engineer"],
    "data science": ["Data Scientist", "ML Engineer", "Data Analyst"],
    "sql": ["Data Analyst", "Backend Developer", "Database Engineer"],
    "postgresql": ["Backend Developer", "Database Engineer", "Data Engineer"],
    "mysql": ["Backend Developer", "Database Engineer", "Software Engineer"],
    "mongodb": ["Backend Developer", "Full Stack Developer", "NoSQL Engineer"],
    "redis": ["Backend Engineer", "Infrastructure Engineer", "Software Developer"],
    "docker": ["DevOps Engineer", "Backend Developer", "Cloud Engineer"],
    "kubernetes": ["DevOps Engineer", "Platform Engineer", "Cloud Engineer"],
    "aws": ["Cloud Engineer", "DevOps Engineer", "Solutions Architect"],
    "azure": ["Cloud Engineer", "Microsoft Cloud Developer", "DevOps Engineer"],
    "gcp": ["Cloud Engineer", "Google Cloud Developer", "Backend Engineer"],
    "devops": ["DevOps Engineer", "Platform Engineer", "SRE"],
    "golang": ["Go Developer", "Backend Engineer", "Microservices Developer"],
    "go": ["Go Developer", "Backend Engineer", "Software Engineer"],
    "rust": ["Rust Developer", "Systems Engineer", "Backend Developer"],
    "c++": ["C++ Developer", "Systems Engineer", "Game Developer"],
    "embedded": ["Embedded Engineer", "IoT Developer", "Firmware Engineer"],
    "blockchain": ["Blockchain Developer", "Web3 Engineer", "Solidity Developer"],
    "solidity": ["Solidity Developer", "Blockchain Engineer", "Web3 Developer"],
    "cybersecurity": ["Security Engineer", "Cybersecurity Analyst", "Penetration Tester"],
    "ui/ux": ["UI/UX Designer", "Product Designer", "Frontend Designer"],
    "figma": ["UI/UX Designer", "Product Designer", "Design Engineer"],
    "data engineering": ["Data Engineer", "ETL Developer", "Big Data Engineer"],
    "spark": ["Data Engineer", "Big Data Developer", "PySpark Developer"],
    "kafka": ["Data Engineer", "Backend Engineer", "Streaming Developer"],
}

FALLBACK_ROLES = ["Software Engineer", "Software Developer", "Backend Developer"]


def generate_queries(skills: List[str], locations: List[str] = None) -> List[str]:
    """
    Given a list of candidate skills, generate effective job search queries.
    Returns a deduplicated list of query strings.
    """
    if not skills:
        return [f"{r} India" for r in FALLBACK_ROLES]

    if not locations:
        locations = ["India", "Bangalore India", "Hyderabad India", "Remote India"]

    queries = set()

    # Generate role-based queries for top skills
    for skill in skills[:6]:
        skill_lower = skill.lower().strip()
        roles = SKILL_TO_ROLE.get(skill_lower, [f"{skill.title()} Developer"])
        for role in roles[:2]:  # Top 2 roles per skill
            for loc in locations[:2]:  # Top 2 locations
                queries.add(f'"{role}" {loc} jobs')

    # Add combined skill queries for adjacent skills
    if len(skills) >= 2:
        top2 = [s.title() for s in skills[:2]]
        queries.add(f'"{top2[0]}" "{top2[1]}" developer India jobs')

    # Add fresher/senior variants based on seniority signal
    skill_text = " ".join(skills).lower()
    if any(k in skill_text for k in ["senior", "lead", "principal", "architect"]):
        queries.add(f'senior "{skills[0].title()}" developer India')
    else:
        queries.add(f'"{skills[0].title()} developer" India hiring')

    return list(queries)[:12]  # Cap at 12 queries to avoid rate limits
