from typing import Optional
from playwright.async_api import Page
import asyncio

class ClaudeController:
    """
    Abstrahiert die UI von Claude.ai (Page Object Model).
    """
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://claude.ai/"

    async def init_session(self):
        """Navigiert auf die Seite und wartet, bis sie geladen ist."""
        print("[ClaudeController] Navigiere zu Claude...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)
        
        # Moegliche Popups/Welcome-Dialoge wegklicken!
        try:
            print("[ClaudeController] Pruefe auf Popups...")
            # Claude hat manchmal Acknowledgements oder Welcome-Banner
            await self.page.get_by_text("Acknowledge").first.click(timeout=1500)
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
        print("[ClaudeController] Sende Prompt...")
        try:
            # Claude nutzt oft ein contenteditable div (ProseMirror) fuer die Eingabe
            prompt_box = self.page.locator("[contenteditable='true']").first
            await prompt_box.click() # Fokussieren
            await prompt_box.clear()
            # Verwende fill fuer das contenteditable Element
            await prompt_box.fill(prompt)
            await self.page.wait_for_timeout(1000)
            
            # Klicke explizit auf den Sende-Button
            try:
                print("[ClaudeController] Klicke definierten Sende-Button...")
                await self.page.locator('button[aria-label*="Send"]').click(timeout=3000)
            except Exception as e:
                print(f"[ClaudeController] Sende-Button nicht gefunden, fallback auf Enter. Fehler: {e}")
                await self.page.keyboard.press("Enter")
        except Exception as e:
            print(f"[ClaudeController] Fehler beim Senden: {e}")
            await self.magic_touch_pause(10, "Konnte Prompt nicht eingeben oder absenden. Bitte manuell absenden!")

    async def wait_for_response(self, timeout_sec: int = 60) -> str:
        """
        Wartet darauf, dass die Generierung abgeschlossen ist, und extrahiert den Text.
        """
        print("[ClaudeController] Warte auf Antwort...")

        # Warte kurz, damit der Request starten kann
        await self.page.wait_for_timeout(3000)

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            # Checken, ob das Input-Feld wieder bereit/editierbar ist
            try:
                prompt_box = self.page.locator("[contenteditable='true']").first
                if await prompt_box.count() > 0 and await prompt_box.is_editable():
                    # Zusaetzlicher Puffer, damit das DOM sicher fertig aktualisiert ist
                    await self.page.wait_for_timeout(3000)
                    break
            except:
                pass

            await self.page.wait_for_timeout(1000)

        # Antwort extrahieren
        print("[ClaudeController] Extrahiere Text...")
        
        # Waehle die Claude-Nachrichten. Typischerweise haben sie die Klasse .font-claude-message
        assistant_messages = await self.page.locator('.font-claude-message').all()
        if not assistant_messages:
            print("[ClaudeController] Warnung: .font-claude-message nicht gefunden! Versuche generischen Fallback...")
            
            # Fallback auf generische Message-Container
            fallback_messages = await self.page.locator('[data-test-render-message]').all()
            if fallback_messages:
                last_message = fallback_messages[-1]
                result = await last_message.inner_text()
                return result.strip()
            
            # Letzter Fallback
            html = await self.page.content()
            with open("temp/error_dump_claude.html", "w", encoding="utf-8") as f:
                f.write(html)
            return "Fehler: Kein Output gefunden. HTML wurde in temp/error_dump_claude.html abgelegt."

        # Wir wollen den Text der exakt letzten Antwort
        last_message = assistant_messages[-1]
        
        # Extrahieren des Textes
        result = await last_message.inner_text()
        
        print(f"[ClaudeController] Erfolgreich {len(result)} Zeichen extrahiert!")
        return result.strip()
