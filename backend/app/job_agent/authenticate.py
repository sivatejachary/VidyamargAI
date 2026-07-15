import asyncio
import json
import os
import sys
from telethon import TelegramClient
from telethon.sessions import StringSession

CONFIG_PATH = os.path.join(os.path.dirname(__file__), "config.json")

async def authenticate():
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)

    api_id = config["api_id"]
    api_hash = config["api_hash"]
    phone = config["phone"]

    print(f"Connecting to Telegram for phone: {phone}...")
    client = TelegramClient(StringSession(""), api_id, api_hash)
    await client.connect()

    if not await client.is_user_authorized():
        print(f"Sending login code to {phone}...")
        await client.send_code_request(phone)
        code = input("Enter the login code sent to your Telegram app / SMS: ").strip()
        try:
            await client.sign_in(phone, code)
        except Exception as e:
            if "password" in str(e).lower():
                pw = input("2-Step Verification Password required. Enter password: ").strip()
                await client.sign_in(password=pw)
            else:
                raise e

    new_session_str = client.session.save()
    config["telegram_session_string"] = new_session_str
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print("SUCCESS: New session key generated and saved to config.json!")
    await client.disconnect()

if __name__ == "__main__":
    asyncio.run(authenticate())
