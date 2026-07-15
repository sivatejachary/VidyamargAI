"""
Telegram Channel Verifier — Standalone CLI Script

Connects to every channel in telegram_channels.txt, counts accessible
messages, and shows a sample of parsed jobs. Use this to audit your
channel list before running the full discovery pipeline.

Usage:
    cd backend
    python -m app.job_discovery.verify_telegram_channels

    # Test a single channel:
    python -m app.job_discovery.verify_telegram_channels --channel JobsForTechies

    # Test with custom messages limit:
    python -m app.job_discovery.verify_telegram_channels --limit 50

    # Show raw messages instead of parsed jobs:
    python -m app.job_discovery.verify_telegram_channels --raw

Options:
    --channel   NAME    Test only this channel (without @)
    --limit     N       Messages to fetch per channel (default: 20)
    --raw               Print raw message text instead of parsed jobs
    --add       NAME    Add a channel to telegram_channels.txt and exit
    --remove    NAME    Remove a channel from telegram_channels.txt and exit
    --list              Print all configured channels and exit
"""
from __future__ import annotations

import argparse
import asyncio
import sys
import os
from pathlib import Path

# Bootstrap path
_BACKEND = Path(__file__).parent.parent.parent.resolve()
if str(_BACKEND) not in sys.path:
    sys.path.insert(0, str(_BACKEND))
import httpx
from app.core.config import settings
from app.job_discovery.connectors.telegram import (
    TelegramJobsConnector,
    _get_all_channels,
    _load_channels_from_file,
    _parse_job,
    _is_job_message,
    _CHANNELS_FILE,
)


# ─── Channel file management helpers ──────────────────────────────────────────

def cmd_list():
    channels = _load_channels_from_file()
    if not channels:
        print("No channels configured yet.")
        print(f"Edit: {_CHANNELS_FILE}")
        return
    print(f"\n{'#':>4}  Channel")
    print("-" * 40)
    for i, ch in enumerate(channels, 1):
        print(f"{i:>4}  @{ch}")
    print(f"\nTotal: {len(channels)} channel(s)")
    print(f"File:  {_CHANNELS_FILE}")


def cmd_add(channel_name: str):
    clean = channel_name.lstrip("@").strip()
    if not clean:
        print("[ERROR] Channel name is empty.")
        sys.exit(1)

    existing = _load_channels_from_file()
    if clean.lower() in [c.lower() for c in existing]:
        print(f"[SKIP] @{clean} already exists in the channels list.")
        return

    with open(_CHANNELS_FILE, "a", encoding="utf-8") as f:
        f.write(f"\n{clean}\n")
    print(f"[ADDED] @{clean} → {_CHANNELS_FILE}")


def cmd_remove(channel_name: str):
    clean = channel_name.lstrip("@").strip()
    existing = _load_channels_from_file()
    if clean.lower() not in [c.lower() for c in existing]:
        print(f"[NOT FOUND] @{clean} is not in the channels list.")
        sys.exit(1)

    lines_in = _CHANNELS_FILE.read_text(encoding="utf-8").splitlines(keepends=True)
    lines_out = [l for l in lines_in if l.strip().lstrip("@").lower() != clean.lower()]
    _CHANNELS_FILE.write_text("".join(lines_out), encoding="utf-8")
    print(f"[REMOVED] @{clean} from {_CHANNELS_FILE}")


# ─── Async verification ────────────────────────────────────────────────────────

async def verify(
    channel_filter: str | None,
    limit: int,
    raw_mode: bool,
):
    connector = TelegramJobsConnector()

    print("\n" + "=" * 62)
    print("   VIDYAMARG AI — TELEGRAM CHANNEL VERIFIER")
    print("=" * 62)

    # Check session
    tg_client = await connector._connect_telethon()
    use_fallback = False
    if not tg_client:
        print("\n[INFO] Telethon session not available. Using HTTPX web scraping fallback (public channels only).")
        use_fallback = True
    else:
        me = await tg_client.get_me()
        print(f"\n  Logged in as: {me.first_name} (@{me.username or 'NoUsername'})")

    channels = _get_all_channels()
    if channel_filter:
        channels = [channel_filter.lstrip("@")]

    print(f"  Channels to verify: {len(channels)}")
    print(f"  Messages per channel: {limit}")
    print("-" * 62)

    total_msgs = 0
    total_jobs = 0
    results = []

    try:
        # Create a single HTTP client if we need fallback
        async with httpx.AsyncClient(timeout=15.0) as http_client:
            for ch in channels:
                print(f"\n  [*] @{ch} ...", end=" ", flush=True)
                try:
                    if use_fallback:
                        messages = await connector._fetch_via_scrape(http_client, ch)
                    else:
                        messages = await connector._fetch_channel_telethon(tg_client, ch)

                    jobs = connector._messages_to_jobs(messages, max_results=limit)
                    total_msgs += len(messages)
                    total_jobs += len(jobs)
                    status = "[OK]" if messages else "[EMPTY] (no job messages found)"
                    print(f"{status}  {len(messages)} msgs -> {len(jobs)} jobs")

                    results.append({
                        "channel": ch,
                        "messages": len(messages),
                        "jobs": len(jobs),
                        "sample": jobs[:3] if not raw_mode else messages[:3],
                    })

                    if jobs and not raw_mode:
                        for j in jobs[:2]:
                            print(f"     |- Job: {j['title'][:60]} @ {j['company_name'][:30]}")
                            if j['required_skills']:
                                print(f"     |  Skills: {', '.join(j['required_skills'][:5])}")
                            if j['apply_url']:
                                print(f"     |  Apply:  {j['apply_url'][:70]}")

                    elif raw_mode and messages:
                        for msg in messages[:2]:
                            snippet = msg["text"][:150].replace("\n", " ")
                            print(f"     |- Msg: {snippet}...")

                except Exception as exc:
                    print(f"[ERROR] Error: {exc}")

        print("\n" + "=" * 62)
        print(f"  SUMMARY: {len(channels)} channels | {total_msgs} job messages | {total_jobs} parsed jobs")
        print(f"  Channels file: {_CHANNELS_FILE}")
        print("=" * 62 + "\n")

    finally:
        if tg_client:
            await tg_client.disconnect()



# ─── Entry point ──────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Verify and manage Telegram job channels",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("--channel", help="Test only this channel (without @)")
    parser.add_argument("--limit", type=int, default=20, help="Messages per channel (default: 20)")
    parser.add_argument("--raw", action="store_true", help="Show raw messages instead of parsed jobs")
    parser.add_argument("--add", metavar="NAME", help="Add a channel and exit")
    parser.add_argument("--remove", metavar="NAME", help="Remove a channel and exit")
    parser.add_argument("--list", action="store_true", help="List all channels and exit")
    args = parser.parse_args()

    if args.list:
        cmd_list()
        return

    if args.add:
        cmd_add(args.add)
        return

    if args.remove:
        cmd_remove(args.remove)
        return

    asyncio.run(verify(args.channel, args.limit, args.raw))


if __name__ == "__main__":
    main()
