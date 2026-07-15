import os
import sys
import time
import logging
import asyncio
from sqlalchemy.orm import Session

logger = logging.getLogger("app.job_agent.agent")

def run_async(coro):
    """Safely run async coroutine from sync context without event loop conflicts."""
    try:
        loop = asyncio.get_running_loop()
    except RuntimeError:
        loop = None
        
    if loop and loop.is_running():
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(asyncio.run, coro)
            return future.result()
    else:
        return asyncio.run(coro)

async def run_telegram_crawler():
    import sys
    job_agent_dir = os.path.dirname(__file__)
    if job_agent_dir not in sys.path:
        sys.path.insert(0, job_agent_dir)

    import json
    from telethon import TelegramClient
    from telethon.sessions import StringSession
    import db as crawler_db
    import telegram_sync
    
    # 1. Initialize crawler database tables and check columns
    logger.info("Initializing crawler tables locally...")
    crawler_db.init_db()
    
    # 2. Load crawler configuration
    cfg_path = os.path.join(os.path.dirname(__file__), "config.json")
    with open(cfg_path, encoding="utf-8") as f:
        config = json.load(f)
        
    # 3. Connect to Telegram
    logger.info("Connecting to Telegram client using StringSession...")
    session_str = config.get("telegram_session_string", "")
    client = TelegramClient(StringSession(session_str), config["api_id"], config["api_hash"])
    await client.start(phone=config["phone"])
    
    # 4. Resolve channels to crawl
    channels = config.get("channels", [])
    if not channels:
        chan_file = os.path.join(os.path.dirname(__file__), "channel.txt")
        if os.path.exists(chan_file):
            with open(chan_file, "r", encoding="utf-8") as cf:
                channels = [line.strip() for line in cf if line.strip() and not line.strip().startswith("#")]
                
    logger.info(f"Starting crawl for {len(channels)} channels...")
    
    # 5. Crawl channels concurrently
    sem = asyncio.Semaphore(3)
    
    async def scan_one(ch):
        async with sem:
            try:
                await telegram_sync.sync_channel(
                    client, ch,
                    history_limit=200,
                    cutoff_days=7,
                    full=False
                )
            except Exception as e:
                logger.error(f"Failed to crawl channel '{ch}': {e}", exc_info=True)
                
    await asyncio.gather(*[scan_one(ch) for ch in channels])
    await client.disconnect()
    logger.info("Crawl complete. Disconnected Telegram client.")

class JobSyncAgent:
    """
    Job Agent subagent in the Career Intelligence Supervisor pipeline.
    Runs the native Telegram crawler and AI extractor to discover jobs
    and insert them directly into VidyaMarg AI's local database.
    """
    NAME = "JobSyncAgent"

    def run(self, state: dict, db: Session) -> dict:
        t0 = time.time()
        logger.info(f"[{self.NAME}] Triggering native Telegram crawler...")
        
        try:
            # Run the crawler
            run_async(run_telegram_crawler())
            
            state["agent_actions"].append({
                "agent": self.NAME,
                "action": "crawl_jobs",
                "status": "completed",
                "duration_ms": int((time.time() - t0) * 1000),
                "output": "Crawl scan executed successfully on all configured channels.",
            })
            
        except Exception as e:
            logger.error(f"[{self.NAME}] Error: {e}", exc_info=True)
            state["errors"].append(f"{self.NAME}: {str(e)}")
            
        return state
