"""
Telegram Login Tool — One-time interactive authentication for the Telethon session.

Run this ONCE before the Job Discovery pipeline can access Telegram channels:

    cd backend
    python -m app.agents.telegram_login

What it does:
  1. Reads TG_API_ID and TG_API_HASH from your .env file
  2. Asks for your phone number (same number as your Telegram account)
  3. Sends a login code to your Telegram app
  4. Saves the session to backend/app/agents/telegram_session.session
  5. Displays how many channels are configured in telegram_channels.txt

After running this tool, the TelegramJobsConnector will automatically
connect on every discovery run without prompting for credentials again.

Requires: telethon  (pip install telethon)
"""
import os
import sys
import asyncio
from pathlib import Path

from telethon import TelegramClient

# Make sure app packages are importable
_BACKEND_DIR = Path(__file__).parent.parent.parent.parent.resolve()
if str(_BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(_BACKEND_DIR))

try:
    from app.core.config import settings
except ImportError:
    sys.path.insert(0, str(_BACKEND_DIR / "backend"))
    from app.core.config import settings


def _count_channels() -> int:
    """Count configured channels in telegram_channels.txt"""
    txt_path = Path(__file__).parent.parent / "job_discovery" / "telegram_channels.txt"
    if not txt_path.exists():
        return 0
    count = 0
    with open(txt_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#"):
                count += 1
    return count


async def main():
    api_id_str = getattr(settings, "TG_API_ID", "") or ""
    api_hash = getattr(settings, "TG_API_HASH", "") or ""

    print("\n" + "=" * 54)
    print("      VIDYAMARG AI — TELEGRAM LOGIN TOOL")
    print("=" * 54)

    if not api_id_str or not api_hash:
        print("\n[ERROR] Telegram credentials not found in .env")
        print("Add the following to your .env file:")
        print("  TG_API_ID=<your_api_id>")
        print("  TG_API_HASH=<your_api_hash>")
        print("\nGet your credentials from: https://my.telegram.org/apps")
        sys.exit(1)

    try:
        api_id = int(api_id_str)
    except ValueError:
        print(f"\n[ERROR] TG_API_ID must be an integer, got: '{api_id_str}'")
        sys.exit(1)

    session_dir = Path(__file__).parent
    session_path = session_dir / "telegram_session"

    channels_count = _count_channels()
    channels_file = session_dir.parent / "job_discovery" / "telegram_channels.txt"

    print(f"\n  API ID:        {api_id}")
    print(f"  Session path:  {session_path}.session")
    print(f"  Channels file: {channels_file}")
    print(f"  Channels configured: {channels_count}")
    print()
    print("This tool will send a login code to your Telegram app.")
    print("Enter your phone number when prompted (with country code, e.g. +919876543210).")
    print("-" * 54)

    client = TelegramClient(str(session_path), api_id, api_hash)

    try:
        await client.start()
        me = await client.get_me()

        if me:
            print("\n[SUCCESS] Authentication completed!")
            print(f"  Logged in as: {me.first_name} {me.last_name or ''} "
                  f"(@{me.username or 'NoUsername'})")
            print(f"  Session saved: {session_path}.session")
            print()
            print(f"  {channels_count} channel(s) configured in telegram_channels.txt")
            print("\nThe discovery pipeline will now automatically connect to:")
            print("  - All public channels in telegram_channels.txt")
            print("  - All PRIVATE channels you have already joined")
            print("  - Groups added via invite links in the .txt file")
            print()
            print("To add more channels, edit:")
            print(f"  {channels_file}")
            print("\nRe-run this tool if your session expires or you change accounts.")
        else:
            print("\n[ERROR] Login failed — could not get user profile. Try again.")

    except KeyboardInterrupt:
        print("\n\nLogin cancelled.")
    except Exception as exc:
        print(f"\n[ERROR] Authentication failed: {exc}")
    finally:
        await client.disconnect()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLogin cancelled by user.")
