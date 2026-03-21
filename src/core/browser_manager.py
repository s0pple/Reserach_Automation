from playwright.async_api import async_playwright, BrowserContext
from typing import AsyncGenerator
import json

class BrowserManager:
    """
    Kapselt das Lifecycle-Management des Playwright-Browsers innerhalb des Docker-Containers.
    """
    def __init__(self, playwright, profile_path: str = "/app/data/browser_sessions/account_baldyboy", headless: bool = True):
        self.playwright = playwright
        self.profile_path = profile_path
        self.headless = headless

    async def start_context(self) -> BrowserContext:
        """Erstellt oder verbindet sich mit dem persistenten Playwright Context."""
        print("[BrowserManager] Starte Browser-Context...")
        
        context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage"
            ],
            viewport={"width": 1280, "height": 720}
        )
        self.context = context
        return context

    async def close(self):
        """Schliesst den Browser sauber und gibt Ressourcen frei."""
        print("[BrowserManager] Schliesse Browser-Context...")
        if hasattr(self, 'context'):
            await self.context.close()
