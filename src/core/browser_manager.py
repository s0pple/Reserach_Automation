import os
from playwright.async_api import BrowserContext
from typing import Optional

class BrowserManager:
    """
    Kapselt das Lifecycle-Management des Playwright-Browsers innerhalb des Docker-Containers.
    """
    def __init__(self, playwright, profile_path: str = "/app/data/browser_sessions/acc1", headless: bool = False):
        self.playwright = playwright
        self.profile_path = profile_path
        self.headless = headless

    async def _clear_singleton_lock(self):
        """Löscht die SingletonLock-Datei, falls sie existiert, um Startfehler zu vermeiden."""
        lock_path = os.path.join(self.profile_path, "SingletonLock")
        if os.path.exists(lock_path):
            print(f"[BrowserManager] Entferne SingletonLock unter {lock_path}...")
            try:
                os.remove(lock_path)
            except Exception as e:
                print(f"[BrowserManager] Warnung: Konnte Lock nicht loeschen: {e}")

    async def start_context(self) -> BrowserContext:
        """Erstellt oder verbindet sich mit dem persistenten Playwright Context."""
        # Wichtig: Erst das Schloss knacken, dann starten
        await self._clear_singleton_lock()
        
        print(f"[BrowserManager] Starte Browser-Context in {self.profile_path}...")
        
        context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=self.headless,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-infobars"
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
