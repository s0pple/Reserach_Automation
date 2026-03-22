from typing import Optional
from playwright.async_api import Page
import asyncio

class MinimaxController:
    """
    Abstrahiert die UI von Minimax (https://agent.minimax.io/).
    """
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://agent.minimax.io/"

    async def init_session(self):
        print("[MinimaxController] Navigiere zu Minimax...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)

    async def magic_touch_pause(self, seconds: int = 20, reason: str = "Unbekannt"):
        print(f"\n[MAGIC TOUCH] Ich stecke fest. Grund: {reason}")
        print(f"[MAGIC TOUCH] Du hast jetzt {seconds} Sekunden Zeit, es im VNC Viewer manuell zu klicken oder zu fixen!")
        for i in range(seconds, 0, -1):
            print(f"... {i} Sekunden uebrig")
            await self.page.wait_for_timeout(1000)
        print("[MAGIC TOUCH] Versuche jetzt weiterzumachen...\n")

    async def set_model(self, model_name: str):
        pass

    async def send_prompt(self, prompt: str):
        print("[MinimaxController] Sende Prompt...")
        try:
            prompt_box = self.page.locator('textarea, [contenteditable="true"]').first
            await prompt_box.click()
            await prompt_box.clear()
            await prompt_box.fill(prompt)
            await self.page.wait_for_timeout(1000)
            
            try:
                await self.page.locator('button:has(svg), div[class*="send"]').last.click(timeout=3000)
            except:
                await self.page.keyboard.press("Enter")
        except Exception as e:
            await self.magic_touch_pause(20, "Konnte Prompt nicht eingeben. Bitte manuell absenden!")

    async def wait_for_response(self, timeout_sec: int = 90) -> str:
        print("[MinimaxController] Warte auf Antwort...")
        await self.page.wait_for_timeout(3000)
        start_time = asyncio.get_event_loop().time()
        last_length = 0
        stable_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            try:
                responses = await self.page.locator('div[class*="message"], div[class*="markdown"]').all()
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

        print("[MinimaxController] Extrahiere Text...")
        assistant_messages = await self.page.locator('div[class*="message"], div[class*="markdown"]').all()
        if not assistant_messages:
            return "Fehler: Kein Output gefunden."
        result = await assistant_messages[-1].inner_text()
        return result.strip()
