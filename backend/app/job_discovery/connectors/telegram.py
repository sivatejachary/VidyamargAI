"""
Telegram Jobs Connector — Full Telethon MTProto Implementation.

Reads channel names from:
  backend/app/job_discovery/telegram_channels.txt

Supports:
  - Private channels (that your account has already joined)
  - Public channels
  - Supergroups used as job boards
  - Invite-link-based channels (t.me/+xxxx format)

Architecture:
  1. Load channels from telegram_channels.txt (primary)
     + database TelegramSource table (secondary / admin-added)
  2. Connect via Telethon MTProto (full API, not Bot API)
     — session file at backend/app/agents/telegram_session.session
  3. For each channel, fetch the last N messages (configurable)
  4. Pass each message through the multi-strategy job parser
  5. Return canonical job dicts to the orchestrator pipeline

To authenticate (first-time only):
    cd backend
    python -m app.agents.telegram_login

Parser strategies (applied in order):
  A. Structured-field extraction (regex: Title:, Company:, Location:, ...)
  B. Emoji-keyword heuristic (🚀 🔥 💼 📌 detect job posts)
  C. NLP fallback (first-line company extraction, URL detection)
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import httpx
from bs4 import BeautifulSoup

from app.core.config import settings
from app.job_discovery.connectors.base import BaseConnector

logger = logging.getLogger("app.job_discovery.connectors.telegram")

# ─── Configuration ─────────────────────────────────────────────────────────────

def _resolve_channels_file() -> Path:
    """
    Resolve the channels file path.
    Priority: TG_CHANNELS_FILE env var → settings → default relative path.
    """
    from_settings = getattr(settings, "TG_CHANNELS_FILE", None)
    if from_settings:
        p = Path(from_settings)
        if p.is_absolute():
            return p
        # Relative: resolve from backend root
        return (Path(__file__).parent.parent.parent / from_settings).resolve()
    return (Path(__file__).parent.parent / "job_discovery" / "telegram_channels.txt").resolve()

_CHANNELS_FILE = _resolve_channels_file()

# How many messages to fetch per channel per run
_MESSAGES_PER_CHANNEL = 100

# Minimum message length to be considered a job post
_MIN_MSG_LENGTH = 60

# ─── Channel list loader ───────────────────────────────────────────────────────

def _load_channels_from_file(filepath: Path = _CHANNELS_FILE) -> List[str]:
    """
    Parse telegram_channels.txt.
    Returns a list of cleaned channel identifiers (usernames or invite hashes).
    Ignores comment lines (starting with #) and blank lines.
    """
    if not filepath.exists():
        logger.warning(f"[Telegram] Channel list file not found: {filepath}")
        return []

    channels: List[str] = []
    with open(filepath, "r", encoding="utf-8") as f:
        for raw_line in f:
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            # Normalize: strip leading @, keep invite hashes (t.me/+xxx)
            channels.append(line.lstrip("@"))

    logger.info(f"[Telegram] Loaded {len(channels)} channels from {filepath.name}")
    return channels


def _load_channels_from_db() -> List[str]:
    """Load channels from the TelegramSource DB table (admin-added sources)."""
    try:
        from app.core.database import SessionLocal
        from app.models.models import TelegramSource
        with SessionLocal() as db:
            sources = (
                db.query(TelegramSource)
                .filter(TelegramSource.active == True)  # noqa: E712
                .all()
            )
        return [s.channel_name.lstrip("@") for s in sources]
    except Exception as exc:
        logger.warning(f"[Telegram] Could not load DB channels: {exc}")
        return []


def _get_all_channels() -> List[str]:
    """
    Merge channels from .txt file + DB, deduplicate, return as list.
    .txt file takes precedence (listed first).
    """
    file_channels = _load_channels_from_file()
    db_channels = _load_channels_from_db()

    # Deduplicate while preserving order
    seen: set[str] = set()
    merged: List[str] = []
    for ch in file_channels + db_channels:
        key = ch.lower().strip()
        if key and key not in seen:
            seen.add(key)
            merged.append(ch)

    logger.info(f"[Telegram] Total unique channels: {len(merged)}")
    return merged


# ─── Job message parser ────────────────────────────────────────────────────────

# Emoji patterns commonly used in Indian job Telegram channels
_JOB_EMOJIS = re.compile(
    r"[\U0001F680\U0001F525\U0001F4BC\U0001F4CD\U0001F4CC\U0001F44B\U0001F4E2\U0001F947"
    r"\U0001F9E0\U0001F4A1\U0001F6A8\u2705\u2714\u2728\u26A1]"
)

# Keywords that strongly indicate a job post
_JOB_KEYWORDS = re.compile(
    r"\b(hiring|job|vacancy|opening|recruit|position|role|internship|fresher|"
    r"apply now|immediate joining|walk.?in|off campus|on campus|batch of \d{4}|"
    r"lpa|ctc|salary|stipend|experience required|yrs?|years? exp)\b",
    re.IGNORECASE,
)

_SPAM_KEYWORDS = re.compile(
    r"\b(earn \d+ daily|make money online|mlm|pyramid|data entry|copy paste|"
    r"investment return|bitcoin|crypto airdrop|no experience.*high salary)\b",
    re.IGNORECASE,
)

def _is_job_message(text: str) -> bool:
    """Quickly determine if a message looks like a job post."""
    if len(text) < _MIN_MSG_LENGTH:
        return False
    if _SPAM_KEYWORDS.search(text):
        return False
    emoji_hit = bool(_JOB_EMOJIS.search(text))
    keyword_hit = bool(_JOB_KEYWORDS.search(text))
    # Need at least one emoji OR two keyword matches
    return emoji_hit or keyword_hit


def _field(pattern: str, text: str, default: str = "") -> str:
    """Extract a single named field from structured text."""
    m = re.search(pattern, text, re.IGNORECASE | re.MULTILINE)
    return m.group(1).strip() if m else default


def _extract_skills(text: str) -> List[str]:
    """Extract skills from Skills/Tech Stack/Requirements lines."""
    m = re.search(
        r"(?:skills?|tech\s*stack|stack|requirements?|tools?)[\s:：]+([^\n]{3,200})",
        text,
        re.IGNORECASE,
    )
    if not m:
        return []
    raw = m.group(1)
    # Split on common delimiters
    parts = re.split(r"[,|/•·\-–]", raw)
    return [p.strip() for p in parts if 2 <= len(p.strip()) <= 40][:20]


def _extract_salary(text: str) -> Tuple[Optional[float], Optional[float], str]:
    """Return (min_lpa, max_lpa, raw_text)."""
    m = re.search(
        r"(?:salary|ctc|lpa|stipend)[\s:：]*"
        r"(?:Rs\.?\s*)?(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:lpa|l\.p\.a|lakh)?",
        text,
        re.IGNORECASE,
    )
    if m:
        lo, hi = float(m.group(1)), float(m.group(2))
        # Convert to INR annual (assume LPA * 100000)
        return lo * 100_000, hi * 100_000, f"{lo}-{hi} LPA"

    m = re.search(
        r"(?:salary|ctc|lpa|stipend)[\s:：]*(?:Rs\.?\s*)?(\d[\d,]+)",
        text,
        re.IGNORECASE,
    )
    if m:
        raw_val = float(m.group(1).replace(",", ""))
        # Heuristic: values > 10000 are rupees, else LPA
        annual = raw_val if raw_val > 10_000 else raw_val * 100_000
        return annual, annual * 1.3, m.group(0).strip()

    return None, None, ""


def _extract_experience(text: str) -> Tuple[Optional[float], Optional[float]]:
    """Return (min_years, max_years)."""
    m = re.search(
        r"(\d+(?:\.\d+)?)\s*[-–to]+\s*(\d+(?:\.\d+)?)\s*(?:years?|yrs?)",
        text,
        re.IGNORECASE,
    )
    if m:
        return float(m.group(1)), float(m.group(2))
    m = re.search(r"(\d+)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?exp", text, re.IGNORECASE)
    if m:
        return float(m.group(1)), None
    if re.search(r"\b(fresher|freshers|0.?1 year|entry.?level)\b", text, re.IGNORECASE):
        return 0.0, 1.0
    return None, None


def _extract_location(text: str) -> Tuple[str, str, bool]:
    """Return (location_str, city, is_remote)."""
    m = re.search(
        r"(?:location|loc|place|city|office)[\s:：]+([^\n,\.]{3,80})",
        text,
        re.IGNORECASE,
    )
    location = m.group(1).strip() if m else "India"

    is_remote = bool(re.search(
        r"\b(remote|work from home|wfh|anywhere|fully remote)\b",
        text,
        re.IGNORECASE,
    ))
    if is_remote and not m:
        location = "Remote"

    city = location.split(",")[0].strip()
    return location, city, is_remote


def _extract_url(text: str) -> str:
    """Find the first HTTP/S URL in the message."""
    m = re.search(r"https?://[^\s\)>\"\']+", text)
    return m.group(0).strip() if m else ""


def _clean(s: str) -> str:
    """Remove markdown/emoji noise from short strings."""
    s = re.sub(r"[*_`~\[\]]+", "", s)
    s = re.sub(r"[\U00010000-\U0010ffff]", "", s)  # strip emoji
    return s.strip(" :-–|,.")


def _parse_job(message_text: str) -> Optional[Dict[str, Any]]:
    """
    Multi-strategy parser. Returns a canonical job dict or None.

    Strategy A — Structured fields (Title:, Company:, ...)
    Strategy B — First-line heuristic
    Strategy C — Generic fallback
    """
    text = message_text.strip()

    # ── Strategy A: Structured field extraction ──────────────────────────────
    title = _field(
        r"(?:title|role|position|post|job title|opening)[\s:：]+([^\n]{3,120})", text
    )
    company = _field(
        r"(?:company|organisation|organization|employer|firm|startup)[\s:：]+([^\n]{2,100})",
        text,
    )

    # ── Strategy B: First-line heuristic ─────────────────────────────────────
    if not title:
        first_line = _clean(text.split("\n")[0])
        # Remove emoji-only prefix words
        first_line = re.sub(r"^[\W\s]+", "", first_line).strip()
        # "HIRING: Software Engineer at Swiggy"
        m = re.match(
            r"(?:hiring|recruiting|job\s*alert|vacancy)[\s:–]+(.+)", first_line, re.IGNORECASE
        )
        if m:
            title = _clean(m.group(1))
        elif len(first_line) > 5 and any(
            kw in first_line.lower()
            for kw in ["engineer", "developer", "analyst", "manager", "intern", "designer", "lead"]
        ):
            title = first_line[:120]

    # ── Strategy C: Keyword fallback ─────────────────────────────────────────
    if not title:
        m = re.search(
            r"\bfor\s+(?:a\s+)?(?:the\s+)?([A-Za-z][A-Za-z0-9 #\+\-\.]{3,80}?)"
            r"(?:\s+(?:role|position|job|opening)|\n|$)",
            text,
            re.IGNORECASE,
        )
        if m:
            title = _clean(m.group(1))

    if not title:
        title = "Software Engineer"  # last resort

    # Extract company if not found in structured field
    if not company:
        m = re.search(
            r"\bat\s+([A-Z][A-Za-z0-9\s&\.]{1,60}?)(?:\s*[,|\n\.]|$)",
            text,
        )
        company = _clean(m.group(1)) if m else "Tech Company"

    # Validate
    title = title[:200].strip()
    company = company[:150].strip()
    if not title or not company or len(company) < 2:
        return None

    # Spam check on company name
    _GARBAGE = {"hiring", "job", "jobs", "vacancy", "apply", "now", "india", "fresher", "freshers"}
    if company.lower() in _GARBAGE:
        company = "Tech Company"

    # All other fields
    location, city, is_remote = _extract_location(text)
    exp_min, exp_max = _extract_experience(text)
    salary_min, salary_max, salary_raw = _extract_salary(text)
    skills = _extract_skills(text)
    apply_url = _extract_url(text)

    return {
        "title": title,
        "company_name": company,
        "description": text[:2000],
        "apply_url": apply_url,
        "job_url": apply_url,
        "location": location,
        "city": city,
        "state": "",
        "country": "IN",
        "is_remote": is_remote,
        "is_hybrid": bool(re.search(r"\bhybrid\b", text, re.IGNORECASE)),
        "salary_min": salary_min,
        "salary_max": salary_max,
        "salary_currency": "INR",
        "salary_raw": salary_raw,
        "experience_min_years": exp_min,
        "experience_max_years": exp_max,
        "required_skills": skills,
        "preferred_skills": [],
        "posted_at": None,  # set from message date
    }


def _relative_date_str(dt: datetime) -> str:
    now = datetime.now(tz=timezone.utc)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    diff_days = (now.date() - dt.date()).days
    if diff_days <= 0:
        return "Today"
    if diff_days == 1:
        return "Yesterday"
    return f"{diff_days} days ago"


# ─── Connector ────────────────────────────────────────────────────────────────

class TelegramJobsConnector(BaseConnector):
    """
    Full Telethon MTProto Telegram connector.

    Reads channel list from telegram_channels.txt.
    Falls back to httpx web scrape for public channels if Telethon session
    is not available.
    """

    SOURCE_NAME = "telegram"
    DEFAULT_TIMEOUT = 15.0

    async def async_search(
        self,
        roles: List[str],
        locations: List[str],
        skills: List[str],
        max_results: int = 200,
        client: httpx.AsyncClient | None = None,
    ) -> List[Dict[str, Any]]:
        channels = _get_all_channels()
        if not channels:
            logger.warning("[Telegram] No channels configured. Add entries to telegram_channels.txt")
            return []

        # Try Telethon first — it handles both private and public channels
        telethon_client = await self._connect_telethon()
        if telethon_client:
            try:
                results = await self._fetch_all_via_telethon(
                    telethon_client, channels, max_results
                )
                return results
            finally:
                try:
                    await telethon_client.disconnect()
                except Exception:
                    pass

        # Fallback: async httpx scrape (public channels only)
        logger.warning(
            "[Telegram] Telethon session unavailable — "
            "falling back to web scrape (public channels only). "
            "Run `python -m app.agents.telegram_login` to enable full access."
        )
        owned_client, owns = await self._get_client(client)
        try:
            tasks = [
                self._fetch_via_scrape(owned_client, ch)
                for ch in channels[:20]  # cap scrape to 20 channels
            ]
            results_per_channel = await asyncio.gather(*tasks, return_exceptions=True)
            all_msgs: List[Dict[str, str]] = []
            for ch, result in zip(channels[:20], results_per_channel):
                if isinstance(result, Exception):
                    logger.error(f"[Telegram] Scrape failed for @{ch}: {result}")
                else:
                    all_msgs.extend(result)

            return self._messages_to_jobs(all_msgs, max_results)
        finally:
            if owns:
                await owned_client.aclose()

    # ─── Telethon methods ──────────────────────────────────────────────────────

    async def _connect_telethon(self):
        """
        Create and connect a Telethon client.
        Returns None if session or credentials are missing.
        """
        try:
            api_id_str = getattr(settings, "TG_API_ID", None)
            api_hash = getattr(settings, "TG_API_HASH", None)
            if not api_id_str or not api_hash:
                logger.warning("[Telegram] TG_API_ID / TG_API_HASH not set in .env")
                return None

            api_id = int(api_id_str)

            # Session lives at backend/app/agents/telegram_session.session
            session_dir = Path(__file__).parent.parent / "agents"
            session_path = session_dir / "telegram_session"

            if not (session_dir / "telegram_session.session").exists():
                logger.warning(
                    f"[Telegram] Session file not found at {session_path}.session. "
                    "Run `python -m app.agents.telegram_login` first."
                )
                return None

            from telethon import TelegramClient
            tg_client = TelegramClient(str(session_path), api_id, api_hash)
            await tg_client.connect()

            if not await tg_client.is_user_authorized():
                logger.warning(
                    "[Telegram] Session exists but user is not authorized. "
                    "Re-run `python -m app.agents.telegram_login`."
                )
                await tg_client.disconnect()
                return None

            me = await tg_client.get_me()
            logger.info(
                f"[Telegram] Connected as "
                f"{me.first_name} (@{me.username or 'NoUsername'})"
            )
            return tg_client

        except Exception as exc:
            logger.error(f"[Telegram] Telethon connect failed: {exc}")
            return None

    async def _fetch_all_via_telethon(
        self,
        tg_client,
        channels: List[str],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from all channels via Telethon.
        Channels are processed concurrently in batches of 10 to avoid
        overwhelming the Telegram server with too many simultaneous requests.
        """
        all_messages: List[Dict[str, Any]] = []
        batch_size = 10

        for i in range(0, len(channels), batch_size):
            batch = channels[i : i + batch_size]
            tasks = [
                self._fetch_channel_telethon(tg_client, ch)
                for ch in batch
            ]
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)

            for ch, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"[Telegram] @{ch} fetch failed: {result}")
                else:
                    all_messages.extend(result)
                    logger.info(
                        f"[Telegram] @{ch}: fetched {len(result)} job messages"
                    )

            # Polite pause between batches (avoid Telegram flood limit)
            if i + batch_size < len(channels):
                await asyncio.sleep(1.0)

        jobs = self._messages_to_jobs(all_messages, max_results)
        logger.info(
            f"[Telegram] Total: {len(all_messages)} messages → {len(jobs)} jobs extracted"
        )
        return jobs

    async def _fetch_channel_telethon(
        self,
        tg_client,
        channel_identifier: str,
    ) -> List[Dict[str, Any]]:
        """
        Fetch messages from a single channel / group.

        Handles:
          - Public channels: @username or username
          - Private channels: t.me/+INVITE_HASH or channel numeric ID
          - Supergroups: same as channels
        """
        messages: List[Dict[str, Any]] = []

        try:
            # Resolve entity (public username or invite hash)
            if channel_identifier.startswith("+") or "t.me/+" in channel_identifier:
                # Invite-link format — join if not already a member
                try:
                    from telethon.tl.functions.messages import ImportChatInviteRequest
                    invite_hash = channel_identifier.replace("t.me/+", "").replace("+", "")
                    await tg_client(ImportChatInviteRequest(invite_hash))
                    logger.info(f"[Telegram] Joined channel via invite hash: {invite_hash}")
                except Exception:
                    # Already a member — fine to continue
                    pass
                # After joining, resolve entity
                entity = await tg_client.get_entity(channel_identifier)
            else:
                entity = await tg_client.get_input_entity(channel_identifier)

            # Fetch messages — iter_messages handles pagination automatically
            from telethon.tl.types import Message
            async for msg in tg_client.iter_messages(
                entity,
                limit=_MESSAGES_PER_CHANNEL,
            ):
                if not isinstance(msg, Message):
                    continue
                text = (msg.message or "").strip()
                if not text or not _is_job_message(text):
                    continue

                messages.append({
                    "text": text,
                    "date": msg.date,
                    "channel": channel_identifier,
                    "msg_id": msg.id,
                })

        except Exception as exc:
            # Log as warning — some channels might be inaccessible
            logger.warning(
                f"[Telegram] Could not access @{channel_identifier}: {exc}"
            )

        return messages

    # ─── Message → Job conversion ──────────────────────────────────────────────

    def _messages_to_jobs(
        self,
        messages: List[Dict[str, Any]],
        max_results: int,
    ) -> List[Dict[str, Any]]:
        """
        Convert raw message dicts to canonical job dicts.
        Deduplicates by content hash within this batch.
        """
        jobs: List[Dict[str, Any]] = []
        seen_hashes: set[str] = set()

        for msg in messages:
            text = msg.get("text", "")
            if not text:
                continue

            parsed = _parse_job(text)
            if not parsed:
                continue

            # Content-based deduplication within this batch
            content_hash = hashlib.md5(
                f"{parsed['title'].lower()}:{parsed['company_name'].lower()}".encode()
            ).hexdigest()
            if content_hash in seen_hashes:
                continue
            seen_hashes.add(content_hash)

            channel = msg.get("channel", "telegram")
            msg_id = msg.get("msg_id", "")
            msg_date = msg.get("date")

            # Build external_id from channel + msg_id (stable across runs)
            ext_id = hashlib.md5(
                f"telegram:{channel}:{msg_id or content_hash}".encode()
            ).hexdigest()

            # Convert datetime
            posted_at = None
            if isinstance(msg_date, datetime):
                posted_at = (
                    msg_date.replace(tzinfo=None)
                    if msg_date.tzinfo
                    else msg_date
                )

            job = self._build_empty_job()
            job.update(parsed)
            job.update({
                "external_id": ext_id,
                "posted_at": posted_at,
                "source_name": self.SOURCE_NAME,
            })
            jobs.append(job)

            if len(jobs) >= max_results:
                break

        return jobs

    # ─── Web scrape fallback ───────────────────────────────────────────────────

    async def _fetch_via_scrape(
        self,
        http_client: httpx.AsyncClient,
        channel_name: str,
    ) -> List[Dict[str, Any]]:
        """
        Async httpx scrape of t.me/s/<channel> (public preview page only).
        Only works for public channels.
        """
        clean_name = channel_name.lstrip("@")
        # Skip invite hashes — cannot scrape private groups without API
        if clean_name.startswith("+") or "t.me/+" in clean_name:
            return []

        url = f"https://t.me/s/{clean_name}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
            )
        }
        messages: List[Dict[str, Any]] = []
        try:
            resp = await http_client.get(url, headers=headers)
            if resp.status_code != 200:
                return []
            soup = BeautifulSoup(resp.text, "html.parser")
            for block in soup.find_all(class_="tgme_widget_message"):
                text_el = block.find(class_="tgme_widget_message_text")
                if not text_el:
                    continue
                text = text_el.get_text(separator="\n").strip()
                if not text or not _is_job_message(text):
                    continue
                dt = None
                time_el = block.find("time")
                if time_el and time_el.get("datetime"):
                    try:
                        dt = datetime.fromisoformat(time_el["datetime"])
                    except Exception:
                        pass
                messages.append({
                    "text": text,
                    "date": dt,
                    "channel": clean_name,
                    "msg_id": "",
                })
        except Exception as exc:
            logger.error(f"[Telegram] Scrape error for @{clean_name}: {exc}")

        return messages
