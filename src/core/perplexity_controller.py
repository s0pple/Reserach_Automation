from typing import Optional
from playwright.async_api import Page
import asyncio

class PerplexityController:
    """
    Abstrahiert die UI von Perplexity (Page Object Model).
    """
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://www.perplexity.ai/"

    async def init_session(self):
        """Navigiert auf die Seite und wartet, bis sie geladen ist."""
        print("[PerplexityController] Navigiere zu Perplexity...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)
        
        # Mögliche Popups/Welcome-Dialoge wegklicken!
        try:
            print("[PerplexityController] Pruefe auf Popups oder Sign-Up Banner...")
            # Perplexity hat oft "Accept Cookies", "Dismiss", "Maybe later", oder ein X-Icon
            # Wir versuchen generisch Escape zu druecken, das schliesst oft Modals
            await self.page.keyboard.press("Escape")
            await self.page.wait_for_timeout(1000)
            
            # Falls ein Button existiert
            for text in ["Accept", "Dismiss", "Maybe later", "Skip"]:
                try:
                    await self.page.get_by_text(text, exact=True).first.click(timeout=1000)
                    await self.page.wait_for_timeout(1000)
                except:
                    pass
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
        """
        Waehlt das Modell (bei Perplexity meist ueber 'Focus' oder 'Pro' Toggle geregelt, 
        oft schwer per Text-Selector zu fassen). Wir nutzen es hier als Dummy/Platzhalter.
        """
        print(f"[PerplexityController] set_model aufgerufen: {model_name} (Dummy)")
        pass

    async def send_prompt(self, prompt: str):
        """Befuellt die Haupt-Eingabe und schickt den Befehl ab."""
        print("[PerplexityController] Sende Prompt...")
        try:
            # Suchen nach Textarea (Perplexity hat oft placeholder "Ask anything...")
            prompt_box = self.page.locator("textarea").first
            await prompt_box.click() # Fokussieren
            await prompt_box.clear()
            await prompt_box.fill(prompt)
            await self.page.wait_for_timeout(1000)
            
            # Klicke explizit auf den Sende-Button
            try:
                print("[PerplexityController] Klicke definierten Sende-Button...")
                # Suchen nach Sende-Button, meist ein Button direkt neben/unter der Textarea, der ein SVG/Icon enthaelt
                await self.page.locator('button[aria-label="Submit"], button:has(svg.fa-arrow-right), button:has(svg)').last.click(timeout=3000)
            except Exception as e:
                print(f"[PerplexityController] Sende-Button nicht gefunden, fallback auf Enter. Fehler: {e}")
                await self.page.keyboard.press("Enter")
        except Exception as e:
            print(f"[PerplexityController] Fehler beim Senden: {e}")
            await self.magic_touch_pause(20, "Konnte Prompt nicht eingeben oder absenden. Bitte manuell absenden!")

    async def wait_for_response(self, timeout_sec: int = 90) -> str:
        """
        Wartet darauf, dass die Generierung abgeschlossen ist, und extrahiert den Text.
        """
        print("[PerplexityController] Warte auf Antwort...")

        # Warte kurz, damit der Request starten kann und die UI umschaltet (z.B. "Searching...")
        await self.page.wait_for_timeout(3000)

        start_time = asyncio.get_event_loop().time()
        last_length = 0
        stable_count = 0

        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            try:
                # Versuch: Pruefen ob sich die Laenge der letzten Antwort noch aendert.
                # Perplexity nutzt oft Tailwind Typography Klassen wie 'prose'
                responses = await self.page.locator('div.prose, div[class*="prose"]').all()
                if responses:
                    current_text = await responses[-1].inner_text()
                    current_length = len(current_text)
                    
                    if current_length > 0 and current_length == last_length:
                        stable_count += 1
                    else:
                        stable_count = 0
                        
                    last_length = current_length
                    
                    # Wenn sich die Laenge 3 Sekunden lang nicht aendert, gehen wir davon aus, dass er fertig ist.
                    # Perplexity hat manchmal noch "Related" Fragen, die ganz am Ende auftauchen.
                    if stable_count >= 3:
                        # Zusaetzlicher Check: Pruefen ob ein typischer Action-Button (Copy, Rewrite, etc.) auftaucht
                        try:
                            action_btns = await self.page.locator('button:has-text("Rewrite"), button[aria-label="Copy"]').count()
                            if action_btns > 0:
                                print("[PerplexityController] Action-Buttons gefunden, Generierung sicher abgeschlossen.")
                                break
                        except:
                            pass
                            
                        print("[PerplexityController] Generierung scheint stabil/abgeschlossen zu sein (Textlaenge).")
                        break
            except Exception as e:
                pass

            await self.page.wait_for_timeout(1000)

        # Antwort extrahieren
        print("[PerplexityController] Extrahiere Text...")
        
        # Waehle die Assistant-Nachrichten (meist innerhalb von 'prose' Containern)
        assistant_messages = await self.page.locator('div.prose, div[class*="prose"]').all()
        
        if not assistant_messages:
            print("[PerplexityController] Warnung: Kein 'prose' Container gefunden! Versuche generischen Fallback...")
            
            # Fallback: Kompletten Chat-Text der letzten Message-Group versuchen
            fallback_messages = await self.page.locator('[data-testid="message-content"], div.break-words').all()
            if fallback_messages:
                result = await fallback_messages[-1].inner_text()
                print(f"[PerplexityController] Fallback extrahiert: {len(result)} Zeichen")
                return result.strip()
            
            # Letzter Fallback
            html = await self.page.content()
            with open("temp/error_dump_perplexity.html", "w", encoding="utf-8") as f:
                f.write(html)
            return "Fehler: Kein Output gefunden. HTML wurde in temp/error_dump_perplexity.html abgelegt."

        # Wir wollen den Text der exakt letzten Antwort
        last_message = assistant_messages[-1]
        
        # Extrahieren des Textes
        result = await last_message.inner_text()
        
        print(f"[PerplexityController] Erfolgreich {len(result)} Zeichen extrahiert!")
        return result.strip()
