import os
import sys
import asyncio
from pathlib import Path

# Ensure backend directory is in path
backend_dir = Path(__file__).parent.resolve()
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Set env to point to local thomas database
os.environ["DATABASE_URL"] = "postgresql://postgres:qPKoMqtzapoyltHQVdheOKyldfbnYrPH@thomas.proxy.rlwy.net:20637/Vidyamargai"

from app.job_agent.agent import run_telegram_crawler

async def main():
    print("Testing Job Agent Telegram Crawler locally...")
    try:
        await run_telegram_crawler()
        print("Telegram crawler execution finished successfully!")
    except Exception as e:
        print(f"Error during crawler test: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
