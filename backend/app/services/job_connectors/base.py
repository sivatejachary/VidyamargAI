"""
Base class and shared data structures for all job connectors.
Uses Google Search exclusively (via googlesearch-python).
Yahoo, DuckDuckGo, and Brave have been removed.
"""
from dataclasses import dataclass
from typing import List, Optional
import re
import urllib.parse
import logging
import hashlib

logger = logging.getLogger(__name__)


@dataclass
class LiveJob:
    """Standardised job record returned by every connector."""
    title: str
    company: str
    location: str
    experience: str          # e.g. "0-2 Years", "3-5 Years", "Fresher"
    skills: List[str]
    apply_url: str
    posted_date: str         # ISO string or human-readable like "2 days ago"
    source: str              # "LinkedIn", "Naukri", "Foundit", etc.
    description: str
    work_mode: str = "On-site"   # "Remote", "Hybrid", "On-site"
    company_logo: Optional[str] = None

    @property
    def stable_id(self) -> str:
        """Deterministic hash ID so the same job always gets the same ID."""
        raw = f"{self.title.lower().strip()}::{self.company.lower().strip()}::{self.source.lower()}"
        return hashlib.md5(raw.encode()).hexdigest()[:16]


# ---------------------------------------------------------------------------
# Google Search (single search engine used across all connectors)
# ---------------------------------------------------------------------------

def google_search(query: str, num_results: int = 15) -> List[dict]:
    """
    Execute a Google search using Serper API (if available) or googlesearch-python as fallback.
    Returns a list of {title, url, snippet} dicts.
    """
    import os
    import requests
    from app.core.config import settings

    serper_key = os.getenv("SERPER_API_KEY") or getattr(settings, "SERPER_API_KEY", None)
    if serper_key:
        try:
            url = "https://google.serper.dev/search"
            headers = {
                "X-API-KEY": serper_key,
                "Content-Type": "application/json"
            }
            payload = {
                "q": query,
                "num": num_results
            }
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                results = []
                for item in data.get("organic", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("link", ""),
                        "snippet": item.get("snippet", "")
                    })
                logger.info(f"Google Serper search returned {len(results)} results for: {query[:60]}")
                return results
        except Exception as e:
            logger.warning(f"Google Serper search failed for query '{query[:60]}': {e}. Falling back to googlesearch-python.")

    results = []
    try:
        from googlesearch import search as _gsearch
        for url in _gsearch(query, num_results=num_results, lang="en"):
            if url:
                results.append({"title": "", "url": url, "snippet": ""})
        logger.info(f"Google search returned {len(results)} results for: {query[:60]}")
    except ImportError:
        logger.error(
            "googlesearch-python is not installed. "
            "Add 'googlesearch-python' to requirements.txt and reinstall."
        )
    except Exception as e:
        logger.warning(f"Google search failed for query '{query[:60]}': {e}")
    return results


# ---------------------------------------------------------------------------
# Backward-compatible shims so connectors that still call
# yahoo_search / extract_yahoo_results continue to work unchanged.
# ---------------------------------------------------------------------------

def clean_query_for_yahoo(query: str) -> str:
    """Translate Google-specific query formats into Yahoo-friendly formats."""
    # site:naukri.com/job-listings- -> site:naukri.com
    query = re.sub(r'site:naukri\.com/job-listings-?', 'site:naukri.com', query)
    
    # site:in.linkedin.com/jobs/view/ -> site:linkedin.com/jobs/view
    query = re.sub(r'site:in\.linkedin\.com/jobs/view/?', 'site:linkedin.com/jobs/view', query)
    
    # site:indeed.com/viewjob OR site:in.indeed.com/rc/clk -> site:indeed.com
    query = re.sub(r'site:indeed\.com/viewjob\s+OR\s+site:in\.indeed\.com/rc/clk', 'site:indeed.com', query)
    
    # site:instahyre.com/jobs/ OR site:instahyre.com/job- -> site:instahyre.com
    query = re.sub(r'site:instahyre\.com/jobs/?\s+OR\s+site:instahyre\.com/job-?', 'site:instahyre.com', query)
    
    # site:cutshort.io/job/ OR site:cutshort.io/jobs -> site:cutshort.io
    query = re.sub(r'site:cutshort\.io/job/?\s+OR\s+site:cutshort\.io/jobs', 'site:cutshort.io', query)
    
    # site:hirist.tech/jobs/ OR site:hirist.com/job/ -> site:hirist.tech
    query = re.sub(r'site:hirist\.tech/jobs/?\s+OR\s+site:hirist\.com/job/?', 'site:hirist.tech', query)
    
    return query


class _GoogleSoupShim:
    """Wraps google results so existing extract_yahoo_results callers still work."""
    def __init__(self, results: List[dict]):
        self._results = results


def yahoo_search(query: str, headers: dict = None, timeout: int = 10):
    """
    Execute a Yahoo search query and return a BeautifulSoup object.
    If it fails, falls back to Google search.
    """
    import requests
    from bs4 import BeautifulSoup
    
    translated_query = clean_query_for_yahoo(query)
    url = f"https://search.yahoo.com/search?p={urllib.parse.quote(translated_query)}&n=15"
    req_headers = headers or COMMON_HEADERS
    
    try:
        resp = requests.get(url, headers=req_headers, timeout=timeout)
        if resp.status_code == 200:
            logger.info(f"Yahoo search returned status 200 for: {translated_query[:60]}")
            return BeautifulSoup(resp.text, "html.parser")
        else:
            logger.warning(f"Yahoo search returned status {resp.status_code} for query: {translated_query[:60]}. Falling back to Google.")
    except Exception as e:
        logger.warning(f"Yahoo search failed for query '{translated_query[:60]}': {e}. Falling back to Google.")
        
    return _GoogleSoupShim(google_search(query, num_results=15))


def extract_yahoo_results(soup) -> List[dict]:
    """
    Backward-compat extractor — works with _GoogleSoupShim or None.
    """
    if soup is None:
        return []
    if isinstance(soup, _GoogleSoupShim):
        return soup._results
    # Legacy BeautifulSoup path (not reached in normal operation)
    results = []
    for r in soup.find_all("div", class_="algo"):
        a_tag = r.find("a")
        if not a_tag:
            continue
        h3 = r.find("h3")
        title_text = h3.text.strip() if h3 else a_tag.text.strip()
        yahoo_link = a_tag.get("href", "")
        snippet_elem = (
            r.find("div", class_="compText")
            or r.find("p")
            or r.find("span", class_="fc-lh")
        )
        snippet = snippet_elem.text.strip() if snippet_elem else ""
        real_link = yahoo_link
        match = re.search(r"/RU=([^/]+)", yahoo_link)
        if match:
            real_link = urllib.parse.unquote(match.group(1))
        if title_text and real_link:
            results.append({"title": title_text, "url": real_link, "snippet": snippet})
    return results


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------

def infer_location(text: str, default: str = "India") -> str:
    """Detect Indian city from text."""
    t = text.lower()
    if "bangalore" in t or "bengaluru" in t:
        return "Bangalore, India"
    if "mumbai" in t:
        return "Mumbai, India"
    if "pune" in t:
        return "Pune, India"
    if "hyderabad" in t:
        return "Hyderabad, India"
    if "chennai" in t:
        return "Chennai, India"
    if "delhi" in t or "noida" in t or "gurgaon" in t or "gurugram" in t:
        return "Delhi NCR, India"
    if "kolkata" in t:
        return "Kolkata, India"
    if "ahmedabad" in t:
        return "Ahmedabad, India"
    if "remote" in t:
        return "Remote, India"
    return default


def infer_work_mode(text: str) -> str:
    t = text.lower()
    if "remote" in t:
        return "Remote"
    if "hybrid" in t:
        return "Hybrid"
    return "On-site"


def infer_experience(text: str) -> str:
    t = text.lower()
    if "fresher" in t or "0-1" in t or "entry" in t or "intern" in t or "graduate" in t:
        return "Fresher / 0-1 Yrs"
    if "senior" in t or "lead" in t or "principal" in t or "5+" in t or "6+" in t:
        return "5+ Years"
    if "3-5" in t or "4-6" in t:
        return "3-5 Years"
    if "1-3" in t or "2-4" in t or "mid" in t:
        return "1-3 Years"
    return "Not Specified"


COMMON_HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
}


def infer_source_from_url(url: str, default: str = "Google Search") -> str:
    """Detect source platform from URL."""
    if not url:
        return default
    u = url.lower()
    if "linkedin.com/jobs" in u or "linkedin.com/view" in u:
        return "LinkedIn"
    if "linkedin.com/posts" in u or "linkedin.com/feed" in u:
        return "LinkedIn Post"
    if "t.me/" in u or "telegram.org" in u or "telegram.me" in u:
        return "Telegram"
    if "naukri.com" in u:
        return "Naukri"
    if "indeed.com" in u:
        return "Indeed"
    if "wellfound.com" in u or "angel.co" in u:
        return "Wellfound"
    if "instahyre.com" in u:
        return "Instahyre"
    if "internshala.com" in u:
        return "Internshala"
    if "cutshort.io" in u:
        return "CutShort"
    if "hirist.com" in u or "hirist.tech" in u:
        return "Hirist"
    if "foundit.in" in u or "monsterindia.com" in u:
        return "Foundit"
    if "greenhouse.io" in u:
        return "Greenhouse"
    if "lever.co" in u:
        return "Lever"
    return default


def is_indian_job(location: str, description: str = "") -> bool:
    """Returns True if the job is located in India or remote India."""
    loc = (location or "").lower()
    desc = (description or "").lower()
    
    # List of Indian cities, states and keywords
    indian_keywords = [
        "india", "bangalore", "bengaluru", "hyderabad", "pune", "mumbai", 
        "chennai", "delhi", "noida", "gurgaon", "gurugram", "kolkata", 
        "ahmedabad", "bengal", "karnataka", "telangana", "maharashtra", 
        "tamil nadu", "haryana", "uttar pradesh"
    ]
    
    # List of international countries or locations that are definitely not India
    international_keywords = [
        "usa", "united states", "uk", "united kingdom", "london", "germany", 
        "berlin", "canada", "toronto", "vancouver", "australia", "sydney", 
        "melbourne", "singapore", "dubai", "uae", "europe", "france", "paris",
        "redmond", "seattle", "san francisco", "california", "new york", "austin"
    ]
    
    # Check if foreign keywords are explicitly in the location
    if any(f in loc for f in international_keywords):
        return False
        
    if "remote" in loc:
        # Check if it mentions foreign locations in location/description
        if any(f in desc for f in international_keywords):
            return False
        # If it specifically mentions India or Indian keywords
        if any(ind in desc or ind in loc for ind in indian_keywords):
            return True
        # Remote default is allowed if no foreign keywords exist
        return True
        
    # Check if location contains any Indian keywords
    if any(ind in loc for ind in indian_keywords):
        return True
        
    # If location is empty or generic like "Worldwide", check description
    if not loc or loc in ["worldwide", "global"]:
        if any(ind in desc for ind in indian_keywords):
            return True
        return False # default worldwide is rejected if no explicit India keyword
            
    return False


def is_fresh_job(posted_date: str) -> bool:
    """Returns True if the job was posted within 30 days."""
    if not posted_date:
        return True
    pd = posted_date.lower().strip()
    if "today" in pd or "yesterday" in pd or "hour" in pd or "minute" in pd:
        return True
    
    # E.g. "3 days ago"
    match = re.search(r'(\d+)\s*day', pd)
    if match:
        days = int(match.group(1))
        return days <= 30
        
    # E.g. "1 month ago" or "year"
    if "month" in pd or "year" in pd:
        return False
        
    # Try parsing as ISO/standard date
    try:
        from dateutil import parser
        from datetime import datetime
        dt = parser.parse(posted_date)
        diff = datetime.utcnow() - dt.replace(tzinfo=None)
        return diff.days <= 30
    except Exception:
        pass
        
    return True


def classify_job(title: str, description: str, skills: List[str]) -> dict:
    """Classifies a job into domain, job_type, and career_level."""
    t = (title or "").lower()
    d = (description or "").lower()
    
    # 1. Domain classification
    domain = "Other"
    
    # AI/ML
    if any(k in t for k in ["ai", "ml", "machine learning", "deep learning", "nlp", "computer vision", "data scientist", "data science"]):
        domain = "AI/ML"
    # Software Engineering
    elif any(k in t for k in ["software", "developer", "engineer", "frontend", "backend", "full stack", "fullstack", "devops", "qa", "quality assurance"]):
        domain = "Software Engineering"
    # Civil Engineering
    elif any(k in t for k in ["civil", "site engineer", "quantity surveyor", "structural engineer"]):
        domain = "Civil Engineering"
    # Mechanical Engineering
    elif any(k in t for k in ["mechanical", "cad designer", "ansys", "solidworks"]):
        domain = "Mechanical Engineering"
    # Electrical Engineering
    elif any(k in t for k in ["electrical", "electronics", "embed", "vlsi"]):
        domain = "Electrical Engineering"
    # CA / Chartered Accountant
    elif any(k in t for k in ["ca", "chartered accountant", "auditor", "audit manager"]):
        domain = "Chartered Accountant"
    # Accounting
    elif any(k in t for k in ["accountant", "accounts", "bookkeeper", "accounting"]):
        domain = "Accounting"
    # Finance
    elif any(k in t for k in ["finance", "financial", "investment", "analyst", "treasury"]):
        domain = "Finance"
    # HR
    elif any(k in t for k in ["hr", "human resource", "recruiter", "talent acquisition"]):
        domain = "HR"
    # Marketing
    elif any(k in t for k in ["marketing", "seo", "branding", "social media"]):
        domain = "Marketing"
    # Sales
    elif any(k in t for k in ["sales", "business development", "bde", "account manager"]):
        domain = "Sales"
    # Healthcare
    elif any(k in t for k in ["doctor", "nurse", "healthcare", "medical", "clinical"]):
        domain = "Healthcare"
    # Legal
    elif any(k in t for k in ["legal", "lawyer", "counsel", "compliance"]):
        domain = "Legal"
    # Operations
    elif any(k in t for k in ["operations", "ops", "logistics", "supply chain"]):
        domain = "Operations"
        
    # 2. Job Type
    job_type = "Full-time"
    if "intern" in t or "internship" in t:
        job_type = "Internship"
    elif "contract" in t or "contractor" in t or "freelance" in t:
        job_type = "Contract"
    elif "part time" in t or "part-time" in t:
        job_type = "Part-time"
        
    # 3. Career Level
    career_level = "Mid-level"
    if "intern" in t or "trainee" in t:
        career_level = "Intern"
    elif "junior" in t or "entry" in t or "fresh" in t or "fresher" in t:
        career_level = "Entry-level"
    elif "senior" in t or "sr." in t or "sr " in t or "lead" in t:
        career_level = "Senior"
    elif "principal" in t or "architect" in t or "manager" in t or "director" in t or "head" in t or "vp" in t:
        career_level = "Lead/Management"
        
    return {
        "domain": domain,
        "job_type": job_type,
        "career_level": career_level
    }
