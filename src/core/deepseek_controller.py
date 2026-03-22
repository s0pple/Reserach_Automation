from typing import Optional
from playwright.async_api import Page
import asyncio

class DeepSeekController:
    """
    Abstrahiert die UI von DeepSeek (Page Object Model).
    """
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://chat.deepseek.com/"

    async def init_session(self):
        """Navigiert auf die Seite und wartet, bis sie geladen ist."""
        print("[DeepSeekController] Navigiere zu DeepSeek...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)
        
        # Mögliche Popups/Welcome-Dialoge wegklicken!
        try:
            print("[DeepSeekController] Pruefe auf Popups...")
            # Fallback fuer Banner oder OK Buttons (z.B. "Got it" oder aehnliches)
            await self.page.get_by_text("Got it").first.click(timeout=1500)
            await self.page.wait_for_timeout(1000)
        except:
            pass

    async def magic_touch_pause(self, seconds: int = 20, reason: str = "Unbekannt"):
        """Self-Healing: Pausiert den Vorgang, damit der User im VNC Viewer eingreifen kann (Fallback)."""
        print(f"\n[MAGIC TOUCH] Ich stecke fest. Grund: {reason}")
        print(f"[MAGIC TOUCH] Du hast jetzt {seconds} Sekunden Zeit, es im VNC Viewer manuell zu klicken oder zu fixen!")
        for i in range(seconds, 0, -1):
            print(f"... {i} Sekunden uebrig")
            await self.page.wait_for_timeout(1000)
        print("[MAGIC TOUCH] Versuche jetzt weiterzumachen...\n")

    async def set_model(self, model_name: str):
        """Dummy-Methode fuer DeepSeek (meist gibt es nur ein Modell oder es wird vorab/anders gewaehlt)."""
        print(f"[DeepSeekController] set_model aufgerufen (Dummy): {model_name}")
        pass

    async def send_prompt(self, prompt: str):
        """Befuellt die Haupt-Eingabe und schickt den Befehl ab."""
        print("[DeepSeekController] Sende Prompt...")
        try:
            # Suchen nach Textarea (DeepSeek nutzt oft #chat-input oder eine generische Textarea)
            prompt_box = self.page.locator("textarea").first
            await prompt_box.click() # Fokussieren
            await prompt_box.clear()
            await prompt_box.fill(prompt)
            await self.page.wait_for_timeout(1000)
            
            # Klicke explizit auf den Sende-Button
            try:
                print("[DeepSeekController] Klicke definierten Sende-Button...")
                # Suchen nach Sende-Button, z.B. div.send-button oder ein SVG/Icon Container
                await self.page.locator('div[class*="send"], div[role="button"]:has(svg), button:has(svg)').last.click(timeout=3000)
            except Exception as e:
                print(f"[DeepSeekController] Sende-Button nicht gefunden, fallback auf Enter. Fehler: {e}")
                await self.page.keyboard.press("Enter")
        except Exception as e:
            print(f"[DeepSeekController] Fehler beim Senden: {e}")
            await self.magic_touch_pause(20, "Konnte Prompt nicht eingeben oder absenden. Bitte manuell absenden!")

    async def wait_for_response(self, timeout_sec: int = 90) -> str:
        """
        Wartet darauf, dass die Generierung abgeschlossen ist, und extrahiert den Text.
        """
        print("[DeepSeekController] Warte auf Antwort...")

        # Warte kurz, damit der Request starten kann
        await self.page.wait_for_timeout(3000)

        start_time = asyncio.get_event_loop().time()
        last_length = 0
        stable_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            try:
                # Versuch: Pruefen ob sich die Laenge der letzten Antwort noch aendert
                responses = await self.page.locator('div.markdown-body, div[class*="message-content"], div[class*="md-body"]').all()
                if responses:
                    current_text = await responses[-1].inner_text()
                    current_length = len(current_text)
                    
                    if current_length > 0 and current_length == last_length:
                        stable_count += 1
                    else:
                        stable_count = 0
                        
                    last_length = current_length
                    
                    # Wenn sich die Laenge 3 Sekunden lang nicht aendert, gehen wir davon aus, dass er fertig ist
                    if stable_count >= 3:
                        print("[DeepSeekController] Generierung scheint stabil/abgeschlossen zu sein.")
                        break
            except Exception as e:
                pass

            await self.page.wait_for_timeout(1000)

        # Antwort extrahieren
        print("[DeepSeekController] Extrahiere Text...")
        
        # Waehle die Assistant-Nachrichten
        # DeepSeek nutzt oft markdown-body oder aehnliche Klassen fuer den Content
        assistant_messages = await self.page.locator('div.markdown-body, div[class*="message-content"], div[class*="md-body"]').all()
        
        if not assistant_messages:
            print("[DeepSeekController] Warnung: Keine Assistant-Nachricht gefunden! Versuche generischen Fallback...")
            
            # Letzter Fallback
            html = await self.page.content()
            with open("temp/error_dump_deepseek.html", "w", encoding="utf-8") as f:
                f.write(html)
            return "Fehler: Kein Output gefunden. HTML wurde in temp/error_dump_deepseek.html abgelegt."

        # Wir wollen den Text der exakt letzten Antwort
        last_message = assistant_messages[-1]
        
        # Extrahieren des Textes
        result = await last_message.inner_text()
        
        print(f"[DeepSeekController] Erfolgreich {len(result)} Zeichen extrahiert!")
        return result.strip()
