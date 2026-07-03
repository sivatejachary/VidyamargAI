"""
VidyaMarg AI — Custom API Job Connector Boilerplate
===================================================
A template for integrating structured external partner APIs or premium JSON sources.
Inherits from BaseJobConnector.
"""
from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional
import httpx

from app.job_discovery.connectors.base import BaseJobConnector, ConnectorConfig, ConnectorResult
from app.job_discovery.domain.models import RawJob

logger = logging.getLogger("jd.connectors.custom_api")


class CustomAPIConnector(BaseJobConnector):
    """
    Template connector for integrating high-trust corporate job boards or direct API partners.
    """

    async def authenticate(self) -> bool:
        """
        Verify API keys, tokens, or session endpoints.
        """
        # If API key is provided, assume authenticating or call a /ping endpoint with the header
        if not self.config.api_key:
            logger.debug("[%s] No API key provided, skipping partner auth", self.name)
            return True
        return True

    async def health_check(self) -> bool:
        """
        Lightweight health check against partner status endpoint.
        """
        if not self.config.base_url:
            return False
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                headers = self._request_headers.copy()
                if self.config.api_key:
                    headers["Authorization"] = f"Bearer {self.config.api_key}"
                # Fallback to standard get request to the base URL
                response = await client.get(self.config.base_url, headers=headers)
                return response.status_code < 400
        except Exception as exc:
            logger.warning("[%s] Health check failed: %s", self.name, exc)
            return False

    async def discover_jobs(
        self, query_params: Dict[str, Any]
    ) -> ConnectorResult:
        """
        Fetch raw job objects from partner JSON API.
        """
        if not self.config.base_url:
            return ConnectorResult(
                connector_name=self.name,
                jobs=[],
                success=False,
                error_message="Base URL is not configured",
            )

        jobs: List[RawJob] = []
        try:
            async with httpx.AsyncClient(timeout=self.config.timeout_seconds) as client:
                headers = self._request_headers.copy()
                if self.config.api_key:
                    headers["Authorization"] = f"Bearer {self.config.api_key}"

                params = {}
                if "roles" in query_params:
                    params["q"] = " OR ".join(query_params["roles"][:3])

                response = await client.get(
                    f"{self.config.base_url}/jobs",
                    headers=headers,
                    params=params,
                )
                if response.status_code != 200:
                    return ConnectorResult(
                        connector_name=self.name,
                        jobs=[],
                        success=False,
                        error_message=f"HTTP Error {response.status_code}",
                    )

                data = response.json()
                raw_list = data.get("jobs", []) if isinstance(data, dict) else data

                for raw in raw_list:
                    if len(jobs) >= self.config.max_results:
                        break
                    norm = self.normalize(raw)
                    if norm:
                        jobs.append(norm)

                return ConnectorResult(
                    connector_name=self.name,
                    jobs=jobs,
                    success=True,
                )

        except Exception as exc:
            logger.error("[%s] Failed to discover jobs: %s", self.name, exc)
            return ConnectorResult(
                connector_name=self.name,
                jobs=[],
                success=False,
                error_message=str(exc),
            )

    def normalize(self, raw_payload: Dict[str, Any]) -> Optional[RawJob]:
        """
        Convert partner JSON format to canonical RawJob.
        """
        try:
            external_id = raw_payload.get("id") or raw_payload.get("job_id")
            if not external_id:
                return None

            title = raw_payload.get("title") or raw_payload.get("role")
            company = raw_payload.get("company") or raw_payload.get("company_name")
            if not title or not company:
                return None

            desc = raw_payload.get("description") or raw_payload.get("body") or ""
            apply_url = raw_payload.get("apply_url") or raw_payload.get("url") or ""

            loc = raw_payload.get("location") or ""
            is_remote = raw_payload.get("is_remote") or "remote" in loc.lower()

            return RawJob(
                external_id=self.make_external_id(str(external_id)),
                source_name=self.name,
                title=title,
                company_name=company,
                description=desc,
                apply_url=apply_url,
                location=loc,
                is_remote=is_remote,
                salary_raw=raw_payload.get("salary_string") or "",
                salary_min=self.safe_float(raw_payload.get("salary_min")),
                salary_max=self.safe_float(raw_payload.get("salary_max")),
                required_skills=raw_payload.get("skills", []),
                raw_payload=raw_payload,
            )
        except Exception as exc:
            logger.debug("[%s] Failed to normalize raw payload: %s", self.name, exc)
            return None
