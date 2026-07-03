"""
VidyaMarg AI — Telegram Job Connector
======================================
Reads job postings from well-known Indian tech job Telegram channels
via the public web preview (https://t.me/s/{channel}).

Authentication strategy:
  1. If TG_API_ID + TG_API_HASH are set → Telethon MTProto (full message history)
  2. Otherwise → httpx web scraping of t.me/s/ preview pages (no credentials needed)

Channel list (public, no login required):
  IndiaHiresNow, DevJobsIndia, StartupJobsIndia, RemoteJobsIndia, TechJobsHyd

Design:
  - All network I/O is async (httpx.AsyncClient)
  - All exceptions are caught; failures return ConnectorResult(success=False)
  - No mock/dummy data — if scraping returns 0 results, the result is empty
"""
from __future__ import annotations

import asyncio
import logging
import re
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

from app.job_discovery.connectors.base import (
    BaseJobConnector,
    ConnectorConfig,
    ConnectorResult,
)
from app.job_discovery.domain.models import RawJob

logger = logging.getLogger("jd.connectors.telegram")

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

TELEGRAM_CHANNELS: List[str] = [
    "job4fresherss", "seekeras", "telugujobupdates03", "RisersSquad", "freshershunt",
    "kickcharm", "placementdriveofficial", "jobsvillaa", "codingsolution_IT",
    "engineerjobsindia", "examdiscussionsprep", "internseeker", "walkindrive",
    "jobsinternshipshub", "freshers_opening", "codingsamurai", "thinkcareers",
    "offcampusjobs4u", "gocareers", "goyalarsh", "jobs_and_internships_updates",
    "offcampus_phodenge", "arunchauhanofficial"
]

PREVIEW_BASE_URL = "https://t.me/s/{channel}"
MESSAGES_PER_CHANNEL = 20

# Common role keywords — used to filter loosely relevant messages
ROLE_KEYWORDS: List[str] = [
    "engineer", "developer", "dev", "sde", "swe", "architect",
    "data scientist", "data analyst", "ml", "ai", "backend", "frontend",
    "fullstack", "full stack", "devops", "cloud", "qa", "tester",
    "manager", "lead", "hiring", "job", "opening", "vacancy", "role",
    "position", "opportunity", "apply", "recruiter", "intern",
]

# Regexes for structured field extraction from message text
_RE_TITLE = re.compile(
    r"(?:role|position|title|job)[:\s]*([^\n\r|•–—]{5,80})",
    re.IGNORECASE,
)
_RE_COMPANY = re.compile(
    r"(?:company|org|organization|employer|at)[:\s]+([^\n\r|•–—]{2,60})",
    re.IGNORECASE,
)
_RE_LOCATION = re.compile(
    r"(?:location|loc|city|based in|office)[:\s]+([^\n\r|•–—]{2,60})",
    re.IGNORECASE,
)
_RE_SKILLS = re.compile(
    r"(?:skills?|tech stack|stack|requirements?|experience in)[:\s]+([^\n\r]{5,200})",
    re.IGNORECASE,
)
_RE_APPLY_URL = re.compile(
    r"(https?://[^\s\)\]>\"\']{10,})",
    re.IGNORECASE,
)
# Salary / CTC mention — captured for salary_raw
_RE_SALARY = re.compile(
    r"(?:ctc|salary|package|lpa|lakh)[:\s]*([^\n\r|•–—]{3,40})",
    re.IGNORECASE,
)


class TelegramConnector(BaseJobConnector):
    """
    Discovers jobs from public Telegram job channels.
    Primary strategy: scrape t.me/s/{channel} preview pages.
    Optional upgrade: use Telethon MTProto if credentials are set.
    """

    def __init__(self, config: ConnectorConfig) -> None:
        super().__init__(config)
        self._telethon_available: bool = False
        self._browser_headers: Dict[str, str] = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

    # ------------------------------------------------------------------
    # Contract: authenticate
    # ------------------------------------------------------------------

    async def authenticate(self) -> bool:
        """
        Tries Telethon auth if TG_API_ID / TG_API_HASH are present.
        Falls back to True for web-scraping mode (no credentials needed).
        """
        api_id = self.config.api_key
        api_hash = self.config.api_secret

        if api_id and api_hash:
            try:
                from telethon import TelegramClient  # type: ignore
                # We don't initiate a full session here — just confirm imports
                self._telethon_available = True
                self.logger.info("Telethon available — MTProto mode enabled")
                return True
            except ImportError:
                self.logger.warning(
                    "TG_API_ID/TG_API_HASH set but 'telethon' not installed. "
                    "Falling back to web scraping."
                )
                self._telethon_available = False

        # Web scraping mode — no credentials needed
        self.logger.info("Telegram connector: using public web preview scraping")
        return True

    # ------------------------------------------------------------------
    # Contract: health_check
    # ------------------------------------------------------------------

    async def health_check(self) -> bool:
        """Probes t.me/s/IndiaHiresNow to verify Telegram preview is reachable."""
        probe_url = PREVIEW_BASE_URL.format(channel="IndiaHiresNow")
        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
            ) as client:
                resp = await client.get(probe_url, headers=self._browser_headers)
                healthy = resp.status_code == 200
                self.logger.debug(
                    f"health_check → {probe_url} → HTTP {resp.status_code} | healthy={healthy}"
                )
                return healthy
        except Exception as exc:
            self.logger.warning(f"health_check failed: {exc}")
            return False

    # ------------------------------------------------------------------
    # Contract: discover_jobs
    # ------------------------------------------------------------------

    async def discover_jobs(self, query_params: Dict[str, Any]) -> ConnectorResult:
        """
        Scrapes each channel's preview page, parses job messages, and
        returns up to config.max_results normalized RawJob objects.
        """
        if self._telethon_available:
            try:
                return await self._discover_jobs_telethon(query_params)
            except Exception as exc:
                self.logger.error("Telethon MTProto fetch failed, falling back to web scraping: %s", exc)

        t_start = time.perf_counter()
        jobs: List[RawJob] = []

        try:
            async with httpx.AsyncClient(
                timeout=self.config.timeout_seconds,
                follow_redirects=True,
                headers=self._browser_headers,
            ) as client:
                for channel in TELEGRAM_CHANNELS:
                    if len(jobs) >= self.config.max_results:
                        break
                    try:
                        channel_jobs = await self._scrape_channel(
                            client, channel, query_params
                        )
                        jobs.extend(channel_jobs)
                        self.logger.info(
                            f"[{channel}] scraped {len(channel_jobs)} jobs"
                        )
                    except Exception as ch_exc:
                        self.logger.warning(
                            f"[{channel}] scraping failed: {ch_exc}"
                        )
                    # Polite delay between channels
                    await asyncio.sleep(1.5)

            jobs = jobs[: self.config.max_results]
            latency_ms = int((time.perf_counter() - t_start) * 1000)
            self.logger.info(
                f"discover_jobs complete: {len(jobs)} jobs in {latency_ms}ms"
            )
            return ConnectorResult(
                connector_name=self.name,
                jobs=jobs,
                success=True,
                latency_ms=latency_ms,
            )

        except Exception as exc:
            latency_ms = int((time.perf_counter() - t_start) * 1000)
            self.logger.error(f"discover_jobs fatal error: {exc}", exc_info=True)
            return ConnectorResult(
                connector_name=self.name,
                jobs=[],
                success=False,
                error_message=str(exc),
                latency_ms=latency_ms,
            )

    async def _discover_jobs_telethon(self, query_params: Dict[str, Any]) -> ConnectorResult:
        """
        Connects via MTProto using Telethon and fetches messages.
        """
        import os
        from telethon import TelegramClient

        api_id = int(self.config.api_key)
        api_hash = self.config.api_secret
        bot_token = os.getenv("TG_BOT_TOKEN")
        session_path = os.getenv("TG_SESSION_PATH", "telegram")

        client = TelegramClient(session_path, api_id, api_hash)
        await client.connect()

        if not await client.is_user_authorized():
            if bot_token:
                await client.start(bot_token=bot_token)
                self.logger.info("Telethon authorized successfully using Bot Token")
            else:
                self.logger.warning("Telethon session not authorized and no TG_BOT_TOKEN provided. Cannot use MTProto.")
                await client.disconnect()
                raise RuntimeError("Telethon session not authorized")

        t_start = time.perf_counter()
        jobs: List[RawJob] = []
        role_filter = [r.lower() for r in query_params.get("roles", [])]

        for channel in TELEGRAM_CHANNELS:
            if len(jobs) >= self.config.max_results:
                break
            try:
                self.logger.info("[%s] Fetching messages via MTProto...", channel)
                messages = await client.get_messages(channel, limit=MESSAGES_PER_CHANNEL)
                
                channel_jobs = []
                for msg in messages:
                    if not msg.text:
                        continue
                    text = msg.text
                    if not self._is_job_message(text):
                        continue
                    if role_filter and not self._matches_roles(text, role_filter):
                        continue
                        
                    parsed = self._parse_job_from_message(text, channel)
                    if parsed:
                        raw_job = self.normalize(parsed)
                        if raw_job:
                            channel_jobs.append(raw_job)
                            
                jobs.extend(channel_jobs)
                self.logger.info("[%s] Scraped %d jobs via MTProto", channel, len(channel_jobs))
            except Exception as e:
                self.logger.error("Failed to fetch messages for channel %s via MTProto: %s", channel, e)

        await client.disconnect()

        jobs = jobs[: self.config.max_results]
        latency_ms = int((time.perf_counter() - t_start) * 1000)
        return ConnectorResult(
            connector_name=self.name,
            jobs=jobs,
            success=True,
            latency_ms=latency_ms,
        )

    # ------------------------------------------------------------------
    # Internal: channel scraper
    # ------------------------------------------------------------------

    async def _scrape_channel(
        self,
        client: httpx.AsyncClient,
        channel: str,
        query_params: Dict[str, Any],
    ) -> List[RawJob]:
        """Fetches and parses up to MESSAGES_PER_CHANNEL messages from a channel preview."""
        url = PREVIEW_BASE_URL.format(channel=channel)
        try:
            resp = await client.get(url)
            if resp.status_code != 200:
                self.logger.warning(
                    f"[{channel}] HTTP {resp.status_code}, skipping"
                )
                return []
        except httpx.RequestError as req_err:
            self.logger.warning(f"[{channel}] request error: {req_err}")
            return []

        soup = BeautifulSoup(resp.text, "html.parser")
        message_elements = soup.find_all(
            "div", class_="tgme_widget_message_text", limit=MESSAGES_PER_CHANNEL
        )

        if not message_elements:
            self.logger.debug(f"[{channel}] 0 message elements found")
            return []

        role_filter = [r.lower() for r in query_params.get("roles", [])]
        jobs: List[RawJob] = []

        for elem in message_elements:
            text = elem.get_text(separator="\n", strip=True)
            if not text:
                continue
            if not self._is_job_message(text):
                continue
            if role_filter and not self._matches_roles(text, role_filter):
                continue

            parsed = self._parse_job_from_message(text, channel)
            if not parsed:
                continue

            raw_job = self.normalize(parsed)
            if raw_job:
                jobs.append(raw_job)

        return jobs

    # ------------------------------------------------------------------
    # Internal: message-level parser
    # ------------------------------------------------------------------

    def _parse_job_from_message(
        self, text: str, channel: str
    ) -> Optional[Dict[str, Any]]:
        """
        Regex-based extractor: attempts to pull title/company/location/
        skills/apply_url from a raw Telegram message text.

        Returns a dict ready for normalize(), or None if insufficient data.
        """
        title = self._extract_first(
            [
                _RE_TITLE,
                # Fallback: first non-empty line that looks like a job title
                re.compile(r"^([A-Z][^\n\r]{5,60}(?:engineer|developer|analyst|lead|manager|intern))", re.IGNORECASE | re.MULTILINE),
            ],
            text,
        )
        company = self._extract_first([_RE_COMPANY], text)
        location = self._extract_first([_RE_LOCATION], text)
        skills_raw = self._extract_first([_RE_SKILLS], text)
        salary_raw = self._extract_first([_RE_SALARY], text)

        # Apply URL — take the first URL found in the message
        url_match = _RE_APPLY_URL.search(text)
        apply_url = url_match.group(1) if url_match else ""

        # If we can't determine a title at all, derive one from the message head
        if not title:
            first_line = text.strip().splitlines()[0] if text.strip() else ""
            title = first_line[:100] if first_line else ""

        if not title:
            return None

        # Split skills string by common delimiters
        skills: List[str] = []
        if skills_raw:
            skills = [
                s.strip()
                for s in re.split(r"[,|/•·\n]", skills_raw)
                if s.strip() and len(s.strip()) > 1
            ]
        if not skills:
            skills = self.extract_skills(text)

        # Attempt to extract a date hint (e.g. "Posted: 2024-05-01" or message metadata)
        date_str = self._extract_first(
            [re.compile(r"\b(\d{4}-\d{2}-\d{2}|\d{1,2}[\/\-]\d{1,2}[\/\-]\d{2,4})\b")],
            text,
        )

        return {
            "title": title.strip(),
            "company": (company or "").strip(),
            "location": (location or "").strip(),
            "skills": skills,
            "apply_url": apply_url.strip(),
            "description": text,
            "salary_raw": (salary_raw or "").strip(),
            "date": date_str or "",
            "channel": channel,
        }

    # ------------------------------------------------------------------
    # Contract: normalize
    # ------------------------------------------------------------------

    def normalize(self, raw_payload: Dict[str, Any]) -> Optional[RawJob]:
        """
        Maps a parsed Telegram job dict to a canonical RawJob.
        Returns None if the payload is unusable.
        """
        try:
            title: str = raw_payload.get("title", "").strip()
            company: str = raw_payload.get("company", "").strip()
            location: str = raw_payload.get("location", "").strip()
            description: str = raw_payload.get("description", "")
            apply_url: str = raw_payload.get("apply_url", "")
            skills: List[str] = raw_payload.get("skills", [])
            salary_raw: str = raw_payload.get("salary_raw", "")
            date_str: str = raw_payload.get("date", "")

            if not title:
                return None

            external_id = self.make_external_id(title, company, date_str)

            is_remote = any(
                kw in (location + " " + description).lower()
                for kw in ("remote", "work from home", "wfh")
            )

            posted_at: Optional[datetime] = None
            if date_str:
                for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%d/%m/%y"):
                    try:
                        posted_at = datetime.strptime(date_str, fmt).replace(
                            tzinfo=timezone.utc
                        )
                        break
                    except ValueError:
                        continue

            return RawJob(
                external_id=external_id,
                source_name="telegram",
                title=title,
                company_name=company or "Unknown",
                description=description,
                apply_url=apply_url,
                job_url=apply_url,
                location=location,
                country="IN",
                is_remote=is_remote,
                salary_raw=salary_raw,
                required_skills=skills,
                posted_at=posted_at,
                raw_payload=raw_payload,
            )
        except Exception as exc:
            self.logger.warning(f"normalize() failed: {exc} | payload={raw_payload}")
            return None

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_first(
        patterns: List[re.Pattern[str]], text: str
    ) -> Optional[str]:
        """Tries each regex pattern in order; returns first captured group or None."""
        for pat in patterns:
            m = pat.search(text)
            if m:
                return m.group(1).strip()
        return None

    @staticmethod
    def _is_job_message(text: str) -> bool:
        """Quick heuristic: does the message look like a job posting?"""
        text_lower = text.lower()
        return any(kw in text_lower for kw in ROLE_KEYWORDS)

    @staticmethod
    def _matches_roles(text: str, roles: List[str]) -> bool:
        """Returns True if message text mentions any of the requested role keywords."""
        text_lower = text.lower()
        return any(role in text_lower for role in roles)
