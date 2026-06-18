"""
Browser Pool Manager — production-grade Playwright browser pool.
Supports session persistence, user context isolation, resource reuse,
and robust graceful fallbacks when Playwright or browser binaries are absent.
"""
from __future__ import annotations

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional

logger = logging.getLogger("app.core.browser_pool")

# Detect environment and try to import playwright
PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.async_api import async_playwright, Browser, BrowserContext, Page
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    logger.warning("playwright package is not installed. Browser pool will run in SIMULATION mode.")

class SimulatedPage:
    """Simulated Playwright Page for graceful fallback."""
    def __init__(self, user_id: int):
        self.user_id = user_id

    async def goto(self, url: str, **kwargs) -> Any:
        logger.info(f"[SimulatedBrowser User={self.user_id}] Navigating to: {url}")
        await asyncio.sleep(0.5)
        return {"status": 200, "url": url}

    async def fill(self, selector: str, value: str, **kwargs):
        logger.info(f"[SimulatedBrowser User={self.user_id}] Filling element '{selector}' with: {value}")
        await asyncio.sleep(0.1)

    async def click(self, selector: str, **kwargs):
        logger.info(f"[SimulatedBrowser User={self.user_id}] Clicking element '{selector}'")
        await asyncio.sleep(0.1)

    async def content(self) -> str:
        return "<html><body>Simulated Page Content</body></html>"

    async def screenshot(self, **kwargs) -> bytes:
        return b"mock_screenshot"

    async def close(self):
        logger.info(f"[SimulatedBrowser User={self.user_id}] Closing page")


class SimulatedContext:
    """Simulated Playwright BrowserContext for graceful fallback."""
    def __init__(self, user_id: int):
        self.user_id = user_id
        self.pages: list[SimulatedPage] = []

    async def new_page(self) -> SimulatedPage:
        page = SimulatedPage(self.user_id)
        self.pages.append(page)
        return page

    async def storage_state(self) -> dict:
        return {"cookies": [], "origins": []}

    async def close(self):
        for p in self.pages:
            await p.close()
        self.pages.clear()


class BrowserPoolManager:
    """
    Manages a pool of reusable Chromium browser instances.
    Ensures memory-efficient browser automation by pooling tabs (pages)
    and isolating user states (cookies, localStorage) in discrete contexts.
    """
    _instance: Optional[BrowserPoolManager] = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_browsers: int = 2, max_contexts_per_browser: int = 5):
        if self._initialized:
            return
        self.max_browsers = max_browsers
        self.max_contexts = max_contexts_per_browser
        self.playwright_instance = None
        self.browsers: list[Browser] = []
        self.contexts: dict[str, Any] = {} # Keyed by user_id
        self.lock = asyncio.Lock()
        self.is_simulation = not PLAYWRIGHT_AVAILABLE
        self._initialized = True

    async def start(self):
        """Starts playwright and warms up browser pool instances."""
        if self.is_simulation:
            logger.info("Browser Pool started in SIMULATION mode.")
            return

        async with self.lock:
            try:
                self.playwright_instance = await async_playwright().start()
                for i in range(self.max_browsers):
                    browser = await self.playwright_instance.chromium.launch(
                        headless=True,
                        args=["--disable-gpu", "--no-sandbox", "--disable-dev-shm-usage"]
                    )
                    self.browsers.append(browser)
                logger.info(f"Browser Pool started with {len(self.browsers)} Chromium instances.")
            except Exception as e:
                logger.error(f"Failed to start Playwright: {e}. Falling back to SIMULATION mode.")
                self.is_simulation = True
                self.browsers = []

    async def get_user_context(self, user_id: int) -> BrowserContext | SimulatedContext:
        """Retrieves or creates an isolated context for a user, loading saved cookies if available."""
        user_key = str(user_id)
        
        async with self.lock:
            if user_key in self.contexts:
                return self.contexts[user_key]

            if self.is_simulation:
                context = SimulatedContext(user_id)
                self.contexts[user_key] = context
                return context

            # Pick browser with least contexts
            selected_browser = min(self.browsers, key=lambda b: len(b.contexts))
            
            # Load stored cookies/localstorage state from file if exists
            storage_state = await self._load_storage_state(user_id)
            
            try:
                context = await selected_browser.new_context(
                    viewport={"width": 1280, "height": 800},
                    storage_state=storage_state,
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                self.contexts[user_key] = context
                logger.info(f"Created isolated Playwright context for user {user_id}")
                return context
            except Exception as e:
                logger.error(f"Failed to create Playwright context for user {user_id}: {e}. Falling back to simulation.")
                context = SimulatedContext(user_id)
                self.contexts[user_key] = context
                return context

    async def get_new_page(self, user_id: int) -> Page | SimulatedPage:
        """Opens a new tab/page inside the user's isolated context."""
        context = await self.get_user_context(user_id)
        return await context.new_page()

    async def release_user_context(self, user_id: int, save_state: bool = True):
        """Closes the user's browser context and persists session state (cookies)."""
        user_key = str(user_id)
        async with self.lock:
            if user_key in self.contexts:
                context = self.contexts[user_key]
                if not self.is_simulation and save_state:
                    try:
                        state = await context.storage_state()
                        await self._save_storage_state(user_id, state)
                    except Exception as e:
                        logger.error(f"Failed to save context state for user {user_id}: {e}")
                
                try:
                    await context.close()
                except Exception:
                    pass
                del self.contexts[user_key]
                logger.info(f"Released browser context for user {user_id}")

    async def shutdown(self):
        """Closes all browsers and stops playwright process."""
        async with self.lock:
            for context in list(self.contexts.values()):
                try:
                    await context.close()
                except Exception:
                    pass
            self.contexts.clear()

            for browser in self.browsers:
                try:
                    await browser.close()
                except Exception:
                    pass
            self.browsers.clear()

            if self.playwright_instance:
                try:
                    await self.playwright_instance.stop()
                except Exception:
                    pass
                self.playwright_instance = None
            logger.info("Browser Pool shut down successfully.")

    # State file storage helpers
    def _get_state_path(self, user_id: int) -> str:
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        sessions_dir = os.path.join(base_dir, "storage", "browser_sessions")
        os.makedirs(sessions_dir, exist_ok=True)
        return os.path.join(sessions_dir, f"user_{user_id}_state.json")

    async def _load_storage_state(self, user_id: int) -> Optional[dict]:
        path = self._get_state_path(user_id)
        if os.path.exists(path):
            try:
                loop = asyncio.get_running_loop()
                def read_file():
                    with open(path, "r") as f:
                        return json.load(f)
                return await loop.run_in_executor(None, read_file)
            except Exception as e:
                logger.warning(f"Failed to load storage state for user {user_id}: {e}")
        return None

    async def _save_storage_state(self, user_id: int, state: dict):
        path = self._get_state_path(user_id)
        try:
            loop = asyncio.get_running_loop()
            def write_file():
                with open(path, "w") as f:
                    json.dump(state, f)
            await loop.run_in_executor(None, write_file)
            logger.info(f"Saved session cookies to: {path}")
        except Exception as e:
            logger.error(f"Failed to save storage state for user {user_id}: {e}")

# Global singleton instance
browser_pool = BrowserPoolManager()
