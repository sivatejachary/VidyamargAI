"""RemoteOK public API connector — free, no key required."""
import hashlib
import logging
from typing import List, Dict, Any
import requests

logger = logging.getLogger("app.job_discovery.connectors.remoteok")

REMOTEOK_API = "https://remoteok.com/api"


class RemoteOKConnector:
    """
    RemoteOK public jobs API — completely free, great for remote jobs globally.
    Returns up to 100 jobs per call.
    """

    def search(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_results: int = 50,
    ) -> List[Dict[str, Any]]:
        try:
            resp = requests.get(
                REMOTEOK_API,
                headers={"User-Agent": "VidyaMargAI/1.0 (+https://vidyamarg.ai)"},
                timeout=20,
            )
            if resp.status_code != 200:
                return []

            data = resp.json()
            if not isinstance(data, list):
                return []

            # First item is metadata
            jobs_raw = [j for j in data if isinstance(j, dict) and j.get("slug")]

            # Filter by role relevance
            role_keywords = set()
            for role in roles:
                role_keywords.update(role.lower().split())

            results = []
            for item in jobs_raw[:150]:
                title = item.get("position", "").strip()
                company = item.get("company", "").strip()
                if not title or not company:
                    continue

                # Check relevance
                title_lower = title.lower()
                desc_lower = (item.get("description") or "").lower()
                if not any(kw in title_lower or kw in desc_lower[:300] for kw in role_keywords if len(kw) > 3):
                    continue

                ext_id = hashlib.md5(f"remoteok:{item.get('slug', '')}".encode()).hexdigest()
                tags = item.get("tags", []) or []
                salary_min = None
                salary_max = None
                if item.get("salary_min"):
                    salary_min = float(item["salary_min"])
                if item.get("salary_max"):
                    salary_max = float(item["salary_max"])

                results.append({
                    "external_id": ext_id,
                    "title": title,
                    "company_name": company,
                    "description": item.get("description", ""),
                    "apply_url": item.get("apply_url") or f"https://remoteok.com/{item.get('slug', '')}",
                    "job_url": f"https://remoteok.com/{item.get('slug', '')}",
                    "location": "Remote",
                    "city": "",
                    "state": "",
                    "country": "GLOBAL",
                    "is_remote": True,
                    "required_skills": tags[:15],
                    "preferred_skills": [],
                    "salary_min": salary_min,
                    "salary_max": salary_max,
                    "salary_currency": "USD",
                    "salary_raw": f"${salary_min or 0}-{salary_max or 0}" if salary_min else "",
                    "posted_at": None,
                    "source_name": "remoteok",
                })

                if len(results) >= max_results:
                    break

            return results

        except Exception as e:
            logger.error(f"[RemoteOK] Fetch failed: {e}")
            return []
