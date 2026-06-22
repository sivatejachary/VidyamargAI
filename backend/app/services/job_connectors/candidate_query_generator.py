def generate_queries(domain: str, preferred_roles: List[str]) -> List[str]:
    """
    Generates a list of targeted search queries based on domain and preferred roles.
    """
    roles = preferred_roles if preferred_roles else []
    
    # Fallback to domain-based default roles if preferred_roles is empty
    if not roles:
        if domain:
            roles = [domain, f"{domain} Specialist", f"{domain} Professional"]
        else:
            roles = ["Software Engineer", "Developer"]

    queries = []
    for role in roles[:4]: # Limit to avoid query combinatorial explosion
        # Targeted India queries
        queries.append(f'"{role}" India')
        queries.append(f'"{role}" India jobs')
        queries.append(f'"{role}" Remote India')

    # Deduplicate and return
    seen = set()
    result = []
    for q in queries:
        q_clean = q.strip()
        if q_clean and q_clean.lower() not in seen:
            seen.add(q_clean.lower())
            result.append(q_clean)
            
    return result
