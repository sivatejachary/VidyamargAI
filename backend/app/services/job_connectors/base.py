"""
Base class and shared data structures for all job connectors.
"""
from dataclasses import dataclass, field
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


def yahoo_search(query: str, headers: dict, timeout: int = 10):
    """
    Execute a Yahoo search and return BeautifulSoup parsed HTML.
    Includes retries and jitter to prevent bot-detection status 500/503.
    """
    import requests
    from bs4 import BeautifulSoup
    import time
    import random
    
    url = f"https://search.yahoo.com/search?p={urllib.parse.quote(query)}&n=20"
    actual_timeout = min(timeout, 3)
    
    # Introduce initial small jitter to stagger concurrent threads
    time.sleep(random.uniform(0.05, 0.5))
    
    # Ensure full browser headers are present to prevent 500 errors from Yahoo
    full_headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }
    if headers:
        # Avoid Accept-Encoding values that lead to decoding issues
        filtered_headers = {k: v for k, v in headers.items() if k.lower() != 'accept-encoding'}
        full_headers.update(filtered_headers)
        
    retries = 2
    for attempt in range(retries + 1):
        try:
            res = requests.get(url, headers=full_headers, timeout=actual_timeout)
            if res.status_code == 200:
                return BeautifulSoup(res.content, "html.parser")
            
            logger.warning(
                f"Yahoo search attempt {attempt + 1} returned status {res.status_code} "
                f"for query '{query[:40]}'"
            )
            if attempt < retries:
                # Exponential backoff with jitter
                sleep_time = random.uniform(0.3, 1.0) * (2 ** attempt)
                time.sleep(sleep_time)
        except Exception as e:
            logger.warning(f"Yahoo search attempt {attempt + 1} failed for query '{query[:40]}': {e}")
            if attempt < retries:
                time.sleep(random.uniform(0.2, 0.6))
                
    return None


def extract_yahoo_results(soup) -> List[dict]:
    """
    Extract list of {title, url, snippet} dicts from a Yahoo SERP soup object.
    """
    if soup is None:
        return []
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

        # Decode Yahoo redirect URL
        real_link = yahoo_link
        match = re.search(r"/RU=([^/]+)", yahoo_link)
        if match:
            real_link = urllib.parse.unquote(match.group(1))

        if title_text and real_link:
            results.append({"title": title_text, "url": real_link, "snippet": snippet})
    return results


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
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/115.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}
