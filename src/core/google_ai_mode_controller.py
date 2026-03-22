from typing import Optional
from playwright.async_api import Page
import asyncio

class GoogleAIModeController:
    """
    Abstrahiert den AI Mode der Google Suche.
    Der User drueckt in Chrome ins Suchfeld und waehlt 'AI Mode'.
    """
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://google.com/"

    async def init_session(self):
        print("[GoogleAIModeController] Navigiere zu Google...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)
        
        try:
            print("[GoogleAIModeController] Pruefe auf Cookie-Banner...")
            await self.page.get_by_text("Accept all").first.click(timeout=1500)
            await self.page.wait_for_timeout(1000)
        except:
            pass

    async def magic_touch_pause(self, seconds: int = 25, reason: str = "Unbekannt"):
        print(f"\n[MAGIC TOUCH] Ich stecke fest. Grund: {reason}")
        print(f"[MAGIC TOUCH] Du hast jetzt {seconds} Sekunden Zeit, den AI-Mode Button manuell zu druecken oder den Prompt abzusenden!")
        for i in range(seconds, 0, -1):
            print(f"... {i} Sekunden uebrig")
            await self.page.wait_for_timeout(1000)
        print("[MAGIC TOUCH] Versuche jetzt weiterzumachen...\n")

    async def set_model(self, model_name: str):
        pass

    async def send_prompt(self, prompt: str):
        print("[GoogleAIModeController] Sende Prompt fuer AI Mode...")
        try:
            # 1. Klicke ins normale Suchfeld
            search_box = self.page.locator('textarea[title="Search"], input[name="q"]').first
            await search_box.click()
            await self.page.wait_for_timeout(1000)
            
            # 2. Versuche den AI-Mode-Button zu finden. 
            # Da dieser oft ein dynamisches UI-Element in Chrome selbst oder im Google-DOM ist, 
            # nutzen wir Magic Touch, falls wir ihn nicht per Selektor finden.
            try:
                print("[GoogleAIModeController] Suche AI Mode Button...")
                # Rate moegliche aria-labels oder Texte
                await self.page.locator('button:has-text("Ask Google"), button[aria-label*="AI"]').first.click(timeout=2000)
                await self.page.wait_for_timeout(1000)
            except:
                print("[GoogleAIModeController] AI-Mode Button nicht automatisch gefunden. Bitte manuell druecken!")
                await self.magic_touch_pause(15, "Finde den AI-Mode Button nicht.")

            # 3. Prompt eingeben
            # Wir füllen das aktuell fokussierte Element (oder wieder die Suchbox)
            await self.page.keyboard.type(prompt)
            await self.page.wait_for_timeout(500)
            await self.page.keyboard.press("Enter")
            
        except Exception as e:
            await self.magic_touch_pause(20, "Konnte Prompt nicht absenden.")

    async def wait_for_response(self, timeout_sec: int = 90) -> str:
        print("[GoogleAIModeController] Warte auf AI Overview...")
        await self.page.wait_for_timeout(5000) # AI Overviews brauchen oft einen Moment
        
        start_time = asyncio.get_event_loop().time()
        last_length = 0
        stable_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            try:
                # Suche nach AI Overview Containern
                responses = await self.page.locator('div[data-md="61"], div:has-text("Generative AI is experimental"), span:has-text("AI Overview")').all()
                if responses:
                    current_text = await responses[-1].inner_text()
                    current_length = len(current_text)
                    if current_length > 0 and current_length == last_length:
                        stable_count += 1
                    else:
                        stable_count = 0
                    last_length = current_length
                    if stable_count >= 3:
                        break
            except:
                pass
            await self.page.wait_for_timeout(1000)

        print("[GoogleAIModeController] Extrahiere Text...")
        # Generischer Fallback, wir greifen den ganzen Textbereich ab
        fallback_texts = await self.page.locator('div.g, div[data-sok-type="1"]').all()
        if fallback_texts:
             result = await fallback_texts[0].inner_text()
             return result.strip()
             
        return "Fehler: Konnte AI Overview Text nicht extrahieren."
