"""
Telegram Channels Management API Router
========================================

Endpoints for managing the telegram_channels.txt file and monitoring
Telegram job discovery — viewable from the Admin / Recruiter Portal.

Routes:
  GET  /telegram/channels          - List all configured channels + status
  POST /telegram/channels          - Add one or more channels
  DELETE /telegram/channels/{name} - Remove a channel
  PUT  /telegram/channels/reorder  - Reorder channels (priority)
  POST /telegram/channels/test     - Test-fetch from a single channel
  GET  /telegram/status            - Session status + last run stats
  POST /telegram/trigger           - Manually trigger a discovery run
"""
from __future__ import annotations

import asyncio
import logging
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.core.security import get_current_user
from app.models.models import User

router = APIRouter(prefix="/telegram", tags=["Telegram Job Discovery"])
logger = logging.getLogger("app.api.telegram_channels")

# Channels file absolute path
_CHANNELS_FILE = (
    Path(__file__).parent.parent.parent / "job_discovery" / "telegram_channels.txt"
)
_SESSION_FILE = (
    Path(__file__).parent.parent.parent / "agents" / "telegram_session.session"
)


# ─── Schemas ──────────────────────────────────────────────────────────────────

class ChannelItem(BaseModel):
    name: str = Field(..., description="Channel username (without @) or invite hash")
    comment: Optional[str] = Field(None, description="Optional label / comment")


class AddChannelsRequest(BaseModel):
    channels: List[ChannelItem] = Field(
        ..., description="List of channels to add"
    )


class TriggerRequest(BaseModel):
    max_messages_per_channel: int = Field(
        100, ge=10, le=500,
        description="How many messages to fetch per channel"
    )
    roles: List[str] = Field(
        default=["Software Engineer", "Backend Engineer", "Full Stack Developer"],
        description="Role keywords to filter job messages"
    )


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _read_channels_file() -> List[Dict[str, Any]]:
    """
    Parse telegram_channels.txt and return structured list.
    Each entry: {name, comment, section, line_number}
    """
    if not _CHANNELS_FILE.exists():
        return []

    results: List[Dict[str, Any]] = []
    current_section = "General"
    line_num = 0

    with open(_CHANNELS_FILE, "r", encoding="utf-8") as f:
        for raw_line in f:
            line_num += 1
            line = raw_line.strip()

            if not line:
                continue

            # Section header: # ─── SECTION NAME ──
            if line.startswith("#"):
                section_match = re.match(r"#\s*[-─\u2500]+\s*(.+?)\s*[-─\u2500]*$", line)
                if section_match:
                    current_section = section_match.group(1).strip()
                continue

            # Channel entry
            results.append({
                "name": line.lstrip("@"),
                "section": current_section,
                "line_number": line_num,
                "url": f"https://t.me/{line.lstrip('@')}",
            })

    return results


def _channel_exists(channel_name: str) -> bool:
    clean = channel_name.lstrip("@").lower().strip()
    for ch in _read_channels_file():
        if ch["name"].lower() == clean:
            return True
    return False


def _append_channels_to_file(channels: List[ChannelItem]) -> List[str]:
    """Append new channels to the end of the .txt file."""
    added: List[str] = []
    with open(_CHANNELS_FILE, "a", encoding="utf-8") as f:
        f.write("\n# ─── Added via API ───────────────────────────────────────────────\n")
        for ch in channels:
            clean = ch.name.lstrip("@").strip()
            if not clean:
                continue
            if _channel_exists(clean):
                logger.info(f"[Channels API] @{clean} already exists, skipping.")
                continue
            line = clean
            if ch.comment:
                f.write(f"# {ch.comment}\n")
            f.write(f"{line}\n")
            added.append(clean)
    return added


def _remove_channel_from_file(channel_name: str) -> bool:
    """Remove a channel line from the .txt file. Returns True if found."""
    if not _CHANNELS_FILE.exists():
        return False

    clean = channel_name.lstrip("@").lower().strip()
    lines_in: List[str] = []
    found = False

    with open(_CHANNELS_FILE, "r", encoding="utf-8") as f:
        lines_in = f.readlines()

    lines_out: List[str] = []
    skip_next_comment = False

    for i, line in enumerate(lines_in):
        stripped = line.strip().lstrip("@")
        if stripped.lower() == clean:
            found = True
            # Also remove the immediately preceding comment line if it's a label
            if lines_out and lines_out[-1].strip().startswith("#"):
                prev = lines_out[-1].strip()
                # Only remove if it's a short one-liner label (not a section header)
                if len(prev) < 80 and "─" not in prev and "─" not in prev:
                    lines_out.pop()
            continue
        lines_out.append(line)

    if found:
        with open(_CHANNELS_FILE, "w", encoding="utf-8") as f:
            f.writelines(lines_out)

    return found


def _get_session_status() -> Dict[str, Any]:
    """Return info about the Telethon session file."""
    exists = _SESSION_FILE.exists()
    mtime = None
    size_kb = None
    if exists:
        stat = _SESSION_FILE.stat()
        mtime = datetime.utcfromtimestamp(stat.st_mtime).isoformat()
        size_kb = round(stat.st_size / 1024, 1)

    return {
        "session_exists": exists,
        "session_path": str(_SESSION_FILE),
        "session_modified_at": mtime,
        "session_size_kb": size_kb,
        "login_command": "cd backend && python -m app.agents.telegram_login",
    }


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/channels", summary="List all configured Telegram channels")
async def list_channels(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns all channels from telegram_channels.txt with their section grouping.
    """
    channels = _read_channels_file()
    # Group by section
    sections: Dict[str, List[Dict]] = {}
    for ch in channels:
        sec = ch["section"]
        if sec not in sections:
            sections[sec] = []
        sections[sec].append({
            "name": ch["name"],
            "url": ch["url"],
        })

    return {
        "total": len(channels),
        "channels_file": str(_CHANNELS_FILE),
        "session_status": _get_session_status(),
        "sections": sections,
        "channels": [{"name": c["name"], "section": c["section"], "url": c["url"]} for c in channels],
    }


@router.post("/channels", summary="Add channels to telegram_channels.txt")
async def add_channels(
    body: AddChannelsRequest,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Appends one or more channel usernames to telegram_channels.txt.

    Channels must be usernames (without @) or invite hashes (t.me/+xxxx).
    The account must have already joined private channels in the Telegram app.
    """
    if not _CHANNELS_FILE.exists():
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Channels file not found: {_CHANNELS_FILE}",
        )

    added = _append_channels_to_file(body.channels)

    return {
        "success": True,
        "added": added,
        "skipped_duplicates": [
            ch.name.lstrip("@") for ch in body.channels
            if ch.name.lstrip("@") not in added
        ],
        "total_channels": len(_read_channels_file()),
        "message": (
            f"Added {len(added)} channel(s). "
            "They will be included in the next discovery run."
        ),
    }


@router.delete(
    "/channels/{channel_name}",
    summary="Remove a channel from telegram_channels.txt",
)
async def remove_channel(
    channel_name: str,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Removes the specified channel from telegram_channels.txt by name.
    """
    found = _remove_channel_from_file(channel_name)
    if not found:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Channel '@{channel_name}' not found in the channels list.",
        )
    return {
        "success": True,
        "removed": channel_name.lstrip("@"),
        "total_channels": len(_read_channels_file()),
    }


@router.get("/status", summary="Telegram session & discovery status")
async def get_telegram_status(
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Returns Telethon session status, channel count, and last discovery stats.
    """
    from app.core.database import SessionLocal
    from app.models.job_models import Job, JobSource

    channels = _read_channels_file()
    session_info = _get_session_status()

    # Get Telegram source stats from DB
    source_stats = None
    try:
        with SessionLocal() as db:
            tg_source = (
                db.query(JobSource)
                .filter(JobSource.name == "telegram")
                .first()
            )
            if tg_source:
                source_stats = {
                    "is_active": tg_source.is_active,
                    "health_score": tg_source.health_score,
                    "consecutive_failures": tg_source.consecutive_failures,
                    "total_jobs_discovered": tg_source.total_jobs_discovered,
                    "total_jobs_accepted": tg_source.total_jobs_accepted,
                    "last_success_at": (
                        tg_source.last_success_at.isoformat()
                        if tg_source.last_success_at else None
                    ),
                    "last_failure_at": (
                        tg_source.last_failure_at.isoformat()
                        if tg_source.last_failure_at else None
                    ),
                }
    except Exception as exc:
        logger.warning(f"Could not load source stats: {exc}")

    return {
        "session": session_info,
        "channels_file": str(_CHANNELS_FILE),
        "total_channels": len(channels),
        "source_stats": source_stats,
        "ready": session_info["session_exists"],
        "hint": (
            None if session_info["session_exists"]
            else "Run `cd backend && python -m app.agents.telegram_login` to authenticate."
        ),
    }


@router.post("/channels/test", summary="Test-fetch jobs from a single channel")
async def test_channel(
    channel_name: str,
    limit: int = 20,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Live test: connects to a single Telegram channel and returns parsed jobs.
    Useful for verifying a new channel before adding it to the discovery list.
    """
    from app.job_discovery.connectors.telegram import TelegramJobsConnector

    connector = TelegramJobsConnector()

    # Temporarily override channels to test just this one
    tg_client = await connector._connect_telethon()
    if not tg_client:
        raise HTTPException(
            status_code=status.HTTP_424_FAILED_DEPENDENCY,
            detail=(
                "Telegram session not available. "
                "Run `python -m app.agents.telegram_login` first."
            ),
        )

    try:
        raw_messages = await connector._fetch_channel_telethon(
            tg_client,
            channel_name.lstrip("@"),
        )
        jobs = connector._messages_to_jobs(raw_messages, max_results=limit)

        return {
            "channel": channel_name.lstrip("@"),
            "messages_fetched": len(raw_messages),
            "jobs_parsed": len(jobs),
            "sample_jobs": [
                {
                    "title": j["title"],
                    "company": j["company_name"],
                    "location": j["location"],
                    "skills": j["required_skills"][:5],
                    "apply_url": j["apply_url"],
                    "salary_raw": j["salary_raw"],
                }
                for j in jobs[:10]
            ],
        }
    finally:
        try:
            await tg_client.disconnect()
        except Exception:
            pass


@router.post("/trigger", summary="Manually trigger a Telegram discovery run")
async def trigger_discovery(
    body: TriggerRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
) -> Dict[str, Any]:
    """
    Triggers an immediate Telegram-only discovery run in the background.
    """
    from app.job_discovery.connectors.telegram import TelegramJobsConnector, _get_all_channels
    from app.job_discovery.normalizer.normalizer import JobNormalizer
    from app.job_discovery.validator.validator import JobValidator
    from app.job_discovery.deduplicator.deduplicator import JobDeduplicator
    from app.job_discovery.persistence.manager import JobPersistenceManager
    from app.job_discovery.events.dispatcher import JobEventDispatcher

    channels = _get_all_channels()
    if not channels:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No channels configured in telegram_channels.txt",
        )

    async def _run_background():
        try:
            connector = TelegramJobsConnector()
            jobs = await connector.async_search(
                roles=body.roles,
                locations=[],
                skills=[],
                max_results=body.max_messages_per_channel * len(channels),
            )

            normalizer = JobNormalizer()
            validator = JobValidator()
            deduplicator = JobDeduplicator()
            persistence = JobPersistenceManager()
            dispatcher = JobEventDispatcher()

            from app.core.database import SessionLocal
            persisted = 0
            with SessionLocal() as db:
                for raw_job in jobs:
                    try:
                        norm = normalizer.normalize(raw_job)
                        if validator.validate(norm):
                            continue
                        if deduplicator.is_duplicate(norm, db):
                            continue
                        job_record = persistence.persist_job(norm, db)
                        db.commit()
                        persisted += 1
                        await dispatcher.publish_persisted(
                            job_id=job_record.id,
                            title=job_record.title,
                            company=job_record.company_name,
                        )
                    except Exception as exc:
                        logger.error(f"[Trigger] Failed to persist job: {exc}")
                        db.rollback()

            logger.info(
                f"[Telegram Trigger] Done: {len(jobs)} parsed, {persisted} persisted."
            )
        except Exception as exc:
            logger.error(f"[Telegram Trigger] Background run failed: {exc}")

    background_tasks.add_task(_run_background)

    return {
        "success": True,
        "channels_count": len(channels),
        "status": "running_in_background",
        "message": (
            f"Telegram discovery triggered for {len(channels)} channel(s). "
            "Jobs will appear in the feed once processing completes."
        ),
    }
