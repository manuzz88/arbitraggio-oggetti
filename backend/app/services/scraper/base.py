from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional
import asyncio
import random
from playwright.async_api import async_playwright, Browser, Page
from loguru import logger

from app.config import settings


class BaseScraper(ABC):
    """Base class per tutti gli scraper"""
    
    def __init__(self):
        self.browser: Optional[Browser] = None
        self.playwright = None
        self._user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:121.0) Gecko/20100101 Firefox/121.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Safari/605.1.15",
        ]
    
    async def start(self):
        """Avvia il browser"""
        self.playwright = await async_playwright().start()
        
        launch_options = {
            "headless": True,
            "args": [
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ]
        }
        
        if settings.PROXY_URL:
            launch_options["proxy"] = {"server": settings.PROXY_URL}
        
        self.browser = await self.playwright.chromium.launch(**launch_options)
        logger.info(f"{self.__class__.__name__} browser started")
    
    async def stop(self):
        """Ferma il browser"""
        if self.browser:
            await self.browser.close()
        if self.playwright:
            await self.playwright.stop()
        logger.info(f"{self.__class__.__name__} browser stopped")
    
    async def create_page(self) -> Page:
        """Crea una nuova pagina con configurazione anti-detection"""
        context = await self.browser.new_context(
            user_agent=random.choice(self._user_agents),
            viewport={"width": 1920, "height": 1080},
            locale="it-IT",
            timezone_id="Europe/Rome",
        )
        
        page = await context.new_page()
        
        # Anti-detection scripts
        await page.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            Object.defineProperty(navigator, 'plugins', {get: () => [1, 2, 3, 4, 5]});
            Object.defineProperty(navigator, 'languages', {get: () => ['it-IT', 'it', 'en-US', 'en']});
        """)
        
        return page
    
    async def random_delay(self, min_sec: float = None, max_sec: float = None):
        """Delay randomizzato per sembrare umano"""
        min_sec = min_sec or settings.SCRAPING_DELAY_MIN
        max_sec = max_sec or settings.SCRAPING_DELAY_MAX
        delay = random.uniform(min_sec, max_sec)
        await asyncio.sleep(delay)
    
    async def human_scroll(self, page: Page):
        """Scroll che simula comportamento umano"""
        for _ in range(random.randint(2, 5)):
            await page.mouse.wheel(0, random.randint(300, 700))
            await asyncio.sleep(random.uniform(0.5, 1.5))
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> List[Dict[str, Any]]:
        """Cerca prodotti - da implementare nelle sottoclassi"""
        pass
    
    @abstractmethod
    async def get_item_details(self, url: str) -> Dict[str, Any]:
        """Ottieni dettagli singolo item - da implementare nelle sottoclassi"""
        pass
    
    @abstractmethod
    async def check_availability(self, url: str) -> bool:
        """Verifica se item è ancora disponibile"""
        pass
