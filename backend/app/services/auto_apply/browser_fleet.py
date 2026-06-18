"""
Browser Fleet Manager — manages headless Chromium browser instances with
anti-detection scripts, rotated fingerprints, and custom user settings.
"""
import asyncio
import random
import logging
from typing import Optional, List, Dict, Tuple, Any
from dataclasses import dataclass

logger = logging.getLogger("app.browser_fleet")

# Real User-Agent strings from common desktop browsers
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

SCREEN_SIZES = [
    (1920, 1080), (1440, 900), (1366, 768),
    (1536, 864), (1280, 800)
]


@dataclass
class BrowserSlot:
    browser: Any          # Playwright Browser instance
    context_count: int    # Number of active contexts
    proxy: Optional[str]  # Proxy configuration string
    fingerprint: Dict[str, Any]


class BrowserFleetManager:
    """Manages a pool of playwright browser slots with rotating fingerprints."""

    def __init__(self, fleet_size: int = 3):
        self.fleet_size = fleet_size
        self.slots: List[BrowserSlot] = []
        self.proxy_pool: List[str] = []
        self._lock = asyncio.Lock()
        self._playwright = None
        self._initialized = False

    async def start(self, proxies: List[str] = None):
        """Initializes the browser slots. Gracefully falls back to mock if Playwright fails."""
        async with self._lock:
            if self._initialized:
                return

            self.proxy_pool = proxies or []
            try:
                from playwright.async_api import async_playwright
                self._playwright = await async_playwright().start()
                
                for i in range(self.fleet_size):
                    proxy = self.proxy_pool[i % len(self.proxy_pool)] if self.proxy_pool else None
                    fp = self._generate_fingerprint()
                    
                    # Setup headless browser launch options
                    launch_args = [
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--no-sandbox",
                        "--disable-gpu",
                        f"--window-size={fp['width']},{fp['height']}"
                    ]
                    
                    browser = await self._playwright.chromium.launch(
                        headless=True,
                        proxy={"server": proxy} if proxy else None,
                        args=launch_args
                    )
                    
                    self.slots.append(BrowserSlot(
                        browser=browser,
                        context_count=0,
                        proxy=proxy,
                        fingerprint=fp
                    ))
                
                self._initialized = True
                logger.info(f"Playwright Browser fleet started successfully with {self.fleet_size} slots.")
            except Exception as e:
                logger.warning(f"Failed to initialize Playwright fleet ({e}). Using mock/dummy slots for safety.")
                self.slots = []
                self._initialized = False

    async def acquire_context(self, user_id: int, portal: str) -> Tuple[Any, Optional[BrowserSlot]]:
        """Acquires a clean browser context with fingerprinting."""
        if not self._initialized or not self.slots:
            logger.debug("Browser fleet not initialized. Returning dummy/mock context.")
            return None, None

        async with self._lock:
            # Pick slot with lowest active contexts
            slot = min(self.slots, key=lambda s: s.context_count)
            fp = slot.fingerprint
            
            context = await slot.browser.new_context(
                viewport={"width": fp["width"], "height": fp["height"]},
                user_agent=fp["user_agent"],
                locale="en-IN",
                timezone_id="Asia/Kolkata",
                extra_http_headers={
                    "Accept-Language": "en-IN,en;q=0.9",
                    "Accept-Encoding": "gzip, deflate, br",
                }
            )
            
            # Inject stealth script to bypass navigator.webdriver detection
            page = await context.new_page()
            await self.inject_stealth_scripts(page)
            await page.close() # Close blank page, keep context warm
            
            slot.context_count += 1
            logger.info(f"Acquired browser context for user {user_id} on {portal}. Active slots: {slot.context_count}")
            return context, slot

    async def release_context(self, context: Any, slot: Optional[BrowserSlot]):
        """Releases the context back to the slot pool."""
        if not context or not slot:
            return
        
        async with self._lock:
            try:
                await context.close()
            except Exception:
                pass
            slot.context_count = max(0, slot.context_count - 1)
            logger.info(f"Released browser context. Slot context count: {slot.context_count}")

    def _generate_fingerprint(self) -> Dict[str, Any]:
        """Generates a randomized desktop browser fingerprint."""
        w, h = random.choice(SCREEN_SIZES)
        return {
            "width": w,
            "height": h,
            "user_agent": random.choice(USER_AGENTS)
        }

    async def inject_stealth_scripts(self, page: Any):
        """Injects custom JS to obscure standard selenium/puppeteer detection variables."""
        if not page:
            return
        try:
            await page.add_init_script("""
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
                Object.defineProperty(navigator, 'languages', {get: () => ['en-IN', 'en']});
                window.chrome = { runtime: {} };
            """)
        except Exception as exc:
            logger.debug(f"Failed to inject stealth scripts (might be mock page): {exc}")

    async def human_delay(self, min_ms: int = 500, max_ms: int = 2000):
        """Adds a randomized delay between actions to simulate human velocity."""
        delay = random.uniform(min_ms / 1000.0, max_ms / 1000.0)
        await asyncio.sleep(delay)

    async def shutdown(self):
        """Closes all browser instances in the pool."""
        async with self._lock:
            for slot in self.slots:
                try:
                    await slot.browser.close()
                except Exception:
                    pass
            self.slots.clear()
            if self._playwright:
                try:
                    await self._playwright.stop()
                except Exception:
                    pass
            self._initialized = False
            logger.info("Browser fleet shut down.")


fleet_manager = BrowserFleetManager(fleet_size=3)
