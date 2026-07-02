import os
import sys
import asyncio
from telethon import TelegramClient

# Add parent directory to sys.path so we can import backend packages
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../")))

try:
    from app.core.config import settings
except ImportError:
    # Fallback if path structure is slightly different
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../")))
    from app.core.config import settings

async def main():
    api_id_str = settings.TG_API_ID
    api_hash = settings.TG_API_HASH

    if not api_id_str or not api_hash:
        print("\n[ERROR] Telegram credentials not found.")
        print("Please check your .env file and ensure that 'api_id' and 'api_hash' are defined.")
        sys.exit(1)

    try:
        api_id = int(api_id_str)
    except ValueError:
        print(f"\n[ERROR] api_id must be an integer, but got: '{api_id_str}'")
        sys.exit(1)

    session_dir = os.path.dirname(os.path.abspath(__file__))
    session_path = os.path.join(session_dir, "telegram_session")

    print("\n==============================================")
    print("        TELEGRAM AGENT LOGIN TOOL")
    print("==============================================")
    print(f"Using API ID: {api_id}")
    print(f"Session path: {session_path}.session")
    print("----------------------------------------------")
    print("This tool will prompt you for your phone number and login code.")
    print("The login code will be sent to your Telegram app.")
    print("==============================================\n")

    client = TelegramClient(session_path, api_id, api_hash)
    
    try:
        await client.start()
        me = await client.get_me()
        if me:
            print("\n[SUCCESS] Authentication completed successfully!")
            print(f"Logged in as: {me.first_name} {me.last_name or ''} (@{me.username or 'NoUsername'})")
            print(f"Session file saved successfully at: {session_path}.session")
            print("Your AI Recruiter Agent is now ready to scrape jobs from Telegram channels/groups!")
        else:
            print("\n[ERROR] Failed to get user profile. Try running again.")
    except Exception as e:
        print(f"\n[ERROR] An error occurred during authentication: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    # Handle event loop properly across different python environments
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nLogin cancelled by user.")
