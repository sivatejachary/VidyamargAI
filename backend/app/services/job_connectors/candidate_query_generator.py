"""
Candidate Query Generator Service.
Maps a candidate's domain and preferred roles to targeted search queries.
"""
from typing import List

def generate_queries(domain: str, preferred_roles: List[str]) -> List[str]:
    """
    Generates a list of targeted search queries based on domain and preferred roles.
    """
    roles = preferred_roles if preferred_roles else []
    
    # Fallback to domain-based default roles if preferred_roles is empty
    if not roles:
        if domain == "AI/ML":
            roles = ["AI Engineer", "ML Engineer", "Data Scientist"]
        elif domain == "Civil Engineering":
            roles = ["Civil Engineer", "Site Engineer"]
        elif domain == "Mechanical Engineering":
            roles = ["Mechanical Engineer", "Design Engineer"]
        elif domain == "Electrical Engineering":
            roles = ["Electrical Engineer", "Embedded Engineer"]
        elif domain == "Chartered Accountant":
            roles = ["Chartered Accountant", "Auditor"]
        elif domain == "Accounting":
            roles = ["Accountant", "Accounts Executive"]
        elif domain == "Finance":
            roles = ["Financial Analyst", "Finance Manager"]
        elif domain == "HR":
            roles = ["HR Generalist", "Recruiter"]
        elif domain == "Marketing":
            roles = ["Marketing Executive", "Digital Marketer"]
        elif domain == "Sales":
            roles = ["Sales Manager", "Business Development Executive"]
        elif domain == "Healthcare":
            roles = ["Healthcare Executive", "Medical Practitioner"]
        elif domain == "Legal":
            roles = ["Legal Counsel", "Lawyer"]
        elif domain == "Operations":
            roles = ["Operations Manager", "Operations Executive"]
        else:
            roles = ["Software Engineer", "Developer"]

    queries = []
    for role in roles[:3]: # Limit to top 3 roles to avoid query combinatorial explosion
        # Targeted India queries
        queries.append(f'"{role}" India')
        queries.append(f'"{role}" India jobs')
        queries.append(f'"{role}" Remote India')
        
        # Add domain specific variations
        if domain == "AI/ML":
            queries.append(f'"{role}" GenAI India')
            queries.append(f'"{role}" Machine Learning India')
        elif domain == "Software Engineering":
            queries.append(f'"{role}" Software India')

    # Deduplicate and return
    seen = set()
    result = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen:
            seen.add(q_clean.lower())
            result.append(q_clean)
            
    return result
