"""
RemoteOK Connector — Async rewrite using httpx.

RemoteOK exposes a free JSON API with no auth required.
All job items are fetched in a single GET call. Relevance filtering
is applied in-process against the requested roles / skills.
"""
from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, List

import httpx

from app.job_discovery.connectors.base import BaseConnector

logger = logging.getLogger("app.job_discovery.connectors.remoteok")

REMOTEOK_API = "https://remoteok.com/api"
_USER_AGENT = "VidyaMargAI/2.0 (+https://vidyamarg.ai)"


class RemoteOKConnector(BaseConnector):
    """
    Async connector for RemoteOK public API.

    A single GET request returns up to ~150 listings.
    We filter by keyword relevance in-process; no extra round-trips.
    """

    SOURCE_NAME = "remoteok"
    DEFAULT_TIMEOUT = 20.0

    async def async_search(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_results: int = 50,
        client: httpx.AsyncClient | None = None,
    ) -> List[Dict[str, Any]]:
        owned_client, owns = await self._get_client(
            client, headers={"User-Agent": _USER_AGENT}
        )
        try:
            resp = await owned_client.get(REMOTEOK_API)
            if resp.status_code != 200:
                logger.warning(f"[RemoteOK] HTTP {resp.status_code}. Skipping.")
                return []

            data = resp.json()
            if not isinstance(data, list):
                logger.warning("[RemoteOK] Unexpected response shape.")
                return []

            # First element is metadata — skip it
            jobs_raw = [j for j in data if isinstance(j, dict) and j.get("slug")]

            # Build keyword set from roles + skills for relevance filtering
            keywords: set[str] = set()
            for r in roles:
                keywords.update(w.lower() for w in r.split() if len(w) > 3)
            for s in skills[:10]:
                keywords.add(s.lower())

            results: List[Dict[str, Any]] = []
            for item in jobs_raw[:200]:
                title = (item.get("position") or "").strip()
                company = (item.get("company") or "").strip()
                if not title or not company:
                    continue

                title_l = title.lower()
                desc_l = (item.get("description") or "")[:400].lower()
                combined = f"{title_l} {desc_l}"
                if keywords and not any(kw in combined for kw in keywords):
                    continue

                slug = item.get("slug", "")
                ext_id = hashlib.md5(f"remoteok:{slug}".encode()).hexdigest()
                tags: List[str] = item.get("tags") or []

                salary_min = float(item["salary_min"]) if item.get("salary_min") else None
                salary_max = float(item["salary_max"]) if item.get("salary_max") else None
                salary_raw = (
                    f"${int(salary_min or 0)}-{int(salary_max or 0)}/yr"
                    if salary_min else ""
                )

                job = self._build_empty_job()
                job.update({
                    "external_id": ext_id,
                    "title": title,
                    "company_name": company,
                    "description": item.get("description", ""),
                    "apply_url": (
                        item.get("apply_url")
                        or f"https://remoteok.com/{slug}"
                    ),
                    "job_url": f"https://remoteok.com/{slug}",
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
                    "salary_raw": salary_raw,
                    "experience_min_years": None,
                    "experience_max_years": None,
                    "posted_at": None,
                    "source_name": self.SOURCE_NAME,
                })
                results.append(job)
                if len(results) >= max_results:
                    break

            logger.info(f"[RemoteOK] Returned {len(results)} relevant jobs.")
            return results

        except httpx.TimeoutException:
            logger.warning("[RemoteOK] Request timed out.")
            return []
        except Exception as exc:
            logger.error(f"[RemoteOK] Fetch failed: {exc}")
            return []
        finally:
            if owns:
                await owned_client.aclose()
