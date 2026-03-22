from typing import Optional
from playwright.async_api import Page
import asyncio

class ChatGPTController:
    """
    Abstrahiert die UI von ChatGPT (Page Object Model).
    """
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://chatgpt.com/"

    async def init_session(self):
        """Navigiert auf die Seite und wartet, bis sie geladen ist."""
        print("[ChatGPTController] Navigiere zu ChatGPT...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)
        
        # Mögliche Popups/Welcome-Dialoge wegklicken!
        try:
            print("[ChatGPTController] Pruefe auf Popups...")
            # ChatGPT hat manchmal "Okay, let's go" oder ähnliche Buttons
            await self.page.get_by_text("Okay, let's go").first.click(timeout=1500)
            await self.page.wait_for_timeout(1000)
        except:
            pass

    async def magic_touch_pause(self, seconds: int = 15, reason: str = "Unbekannt"):
        """Self-Healing: Pausiert den Vorgang, damit der User im VNC Viewer eingreifen kann (Fallback)."""
        print(f"\n[MAGIC TOUCH] Ich stecke fest. Grund: {reason}")
        print(f"[MAGIC TOUCH] Du hast jetzt {seconds} Sekunden Zeit, es im VNC Viewer manuell zu klicken oder zu fixen!")
        for i in range(seconds, 0, -1):
            print(f"... {i} Sekunden uebrig")
            await self.page.wait_for_timeout(1000)
        print("[MAGIC TOUCH] Versuche jetzt weiterzumachen...\n")

    async def send_prompt(self, prompt: str):
        """Befuellt die Haupt-Eingabe und schickt den Befehl ab."""
        print("[ChatGPTController] Sende Prompt...")
        try:
            # Das Prompt-Feld hat bei ChatGPT meist die ID prompt-textarea
            prompt_box = self.page.locator("#prompt-textarea")
            await prompt_box.click() # Fokussieren
            await prompt_box.clear()
            # Verwende type oder fill, je nachdem was robuster bei React ist
            await prompt_box.fill(prompt)
            await self.page.wait_for_timeout(1000)
            
            # Klicke explizit auf den Sende-Button
            try:
                print("[ChatGPTController] Klicke definierten Sende-Button...")
                await self.page.locator('button[data-testid="send-button"]').click(timeout=3000)
            except Exception as e:
                print(f"[ChatGPTController] Sende-Button nicht gefunden, fallback auf Enter. Fehler: {e}")
                await self.page.keyboard.press("Enter")
        except Exception as e:
            print(f"[ChatGPTController] Fehler beim Senden: {e}")
            await self.magic_touch_pause(10, "Konnte Prompt nicht eingeben oder absenden. Bitte manuell absenden!")

    async def wait_for_response(self, timeout_sec: int = 60) -> str:
        """
        Wartet darauf, dass die Generierung abgeschlossen ist, und extrahiert den Text.
        """
        print("[ChatGPTController] Warte auf Antwort...")

        # Warte kurz, damit der Request starten kann
        await self.page.wait_for_timeout(3000)

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            # Checken, ob der Sende-Button wieder klickbar ist oder der Stop-Button verschwunden ist
            try:
                send_btn = self.page.locator('button[data-testid="send-button"]')
                if await send_btn.count() > 0 and await send_btn.is_enabled():
                    # Zusaetzlicher Puffer, damit das DOM sicher fertig aktualisiert ist
                    await self.page.wait_for_timeout(3000)
                    break
            except:
                pass

            await self.page.wait_for_timeout(1000)

        # Antwort extrahieren
        print("[ChatGPTController] Extrahiere Text...")
        
        # Waehle die Assistant-Nachrichten via data-message-author-role attribute
        assistant_messages = await self.page.locator('[data-message-author-role="assistant"]').all()
        if not assistant_messages:
            print("[ChatGPTController] Warnung: Keine Assistant-Nachricht gefunden! Versuche generischen Fallback...")
            
            # Fallback
            html = await self.page.content()
            with open("temp/error_dump.html", "w", encoding="utf-8") as f:
                f.write(html)
            return "Fehler: Kein Output gefunden. HTML wurde in temp/error_dump.html abgelegt."

        # Wir wollen den Text der exakt letzten Antwort
        last_message = assistant_messages[-1]
        
        # Extrahieren des Textes. Playwright's inner_text() holt den lesbaren Text inkl. Zeilenumbrüchen.
        result = await last_message.inner_text()
        
        print(f"[ChatGPTController] Erfolgreich {len(result)} Zeichen extrahiert!")
        return result.strip()
