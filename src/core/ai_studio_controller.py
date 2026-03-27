from typing import Optional
from playwright.async_api import Page
import asyncio
import time

class AIStudioController:
    """
    Abstrahiert die UI von Google AI Studio (Page Object Model).
    """
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://aistudio.google.com/app/prompts/new_chat"

    async def init_session(self):
        """Navigiert auf die Seite und wartet, bis sie geladen ist."""
        print("[AIStudioController] Navigiere zu AI Studio...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await self.page.wait_for_timeout(3000)
        
        # Cookie Banner wegklicken!
        try:
            print("[AIStudioController] Pruefe auf Cookie-Banner...")
            await self.page.get_by_text("Agree").first.click(timeout=1500)
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

    async def set_model(self, model_name: str):
        """Oeffnet das Dropdown und waehlt das spezifische Modell (z.B. 'Gemini 3 Flash')."""
        print(f"[AIStudioController] Setze Modell auf: {model_name}")
        try:
            # Absolute Koordinate f├╝r Fallback auf 1280x720: (1120, 130) ist meist der Dropdown Button
            await self.page.mouse.click(1120, 130)
            await self.page.wait_for_timeout(1000)
            
            # Versuche verschiedene Versionen des Textes (falls er leicht abweicht)
            clicked = False
            for test_name in [model_name, "Gemini 3 Flash", "Gemini 2.5 Flash", "Gemini 1.5 Pro"]:
                try:
                    await self.page.locator("span").filter(has_text=test_name).first.click(timeout=1000)
                    print(f"[AIStudioController] Modell {test_name} ausgewaehlt!")
                    clicked = True
                    break
                except:
                    pass
            if not clicked:
                raise Exception("Modell in der Liste nicht gefunden")
                
        except Exception as e:
            print(f"[AIStudioController] Warnung bei Model Change: {e}")
            await self.magic_touch_pause(10, f"Konnte Modell {model_name} nicht finden/auswaehlen.")

    async def toggle_grounding(self, enable: bool):
        """Aktiviert oder deaktiviert Google Search Grounding."""
        print(f"[AIStudioController] Google Grounding -> {'An' if enable else 'Aus'}")
        search_switch = self.page.get_by_role("switch", name="Google Search")
        if await search_switch.count() > 0:
            is_checked = await search_switch.is_checked()
            if is_checked != enable:
                await search_switch.click()
        else:
            # Fallback falls UI sich aendert
            fallback = self.page.get_by_text("Grounding with Google Search").last
            if fallback:
                await fallback.click()

    async def set_system_instructions(self, instructions: str):
        """Klickt auf 'System instructions' und fuellt das Textfeld."""
        print("[AIStudioController] Setze System Instructions...")
        sys_btn = self.page.locator("button.system-instructions-card")
        if await sys_btn.count() > 0:
            await sys_btn.click()
            await self.page.wait_for_timeout(1000)
        
        # Die erste Textarea ist die System-Instruction Box
        sys_box = self.page.locator("textarea").first
        await sys_box.fill(instructions)

    async def send_prompt(self, prompt: str):
        print("[AIStudioController] Sende Prompt...")
        try:
            prompt_box = self.page.locator("textarea").last
            await prompt_box.click()
            await prompt_box.clear()
            await prompt_box.fill(prompt)
            await self.page.wait_for_timeout(500)

            # Merke dir, wie viele KI-Antworten VOR dem Absenden existieren
            self.turn_count_before = await self.page.locator(".model-turn").count()

            print("[AIStudioController] Druecke Strg+Enter zum Absenden...")
            await self.page.keyboard.press("Control+Enter")
        except Exception as e:
            print(f"[AIStudioController] Fehler beim Senden: {e}")

    async def wait_for_response(self, timeout_sec: int = 60) -> str:
        print("[AIStudioController] Warte auf KI-Generierung...")
        try:
            start_time = time.time()

            # 1. Warten, bis ein neuer Antwort-Block (.model-turn) erscheint
            while time.time() - start_time < timeout_sec:
                current_turns = await self.page.locator(".model-turn").count()
                if current_turns > getattr(self, 'turn_count_before', 0):
                    break
                await self.page.wait_for_timeout(1000)

            # 2. Generierung abwarten (10 Sekunden harter Puffer für den Textaufbau)
            print("[AIStudioController] KI schreibt... warte 10 Sekunden...")
            await self.page.wait_for_timeout(10000)

            # 3. Nur den letzten Modell-Turn auslesen
            model_turns = await self.page.locator(".model-turn").all()
            if not model_turns:
                return "Fehler: Kein .model-turn (KI-Antwort) gefunden."

            text = await model_turns[-1].inner_text()

            for bad_word in ["content_copy", "expand_less", "Markdown", "download", "Copy code"]:
                text = text.replace(bad_word, "")

            result = text.strip()
            print(f"[AIStudioController] Erfolgreich extrahiert ({len(result)} Zeichen).")
            return result
        except Exception as e:
            print(f"[AIStudioController] Fehler beim Scrapen: {e}")
            return "Fehler beim Lesen der Antwort."
        """
        Wartet darauf, dass die Generierung abgeschlossen ist, und extrahiert den Text.
        """
        print("[AIStudioController] Warte auf Antwort...")

        # Warte kurz, damit der "Run" Status ueberhaupt startet (Stop Button erscheint)
        await self.page.wait_for_timeout(3000)

        start_time = asyncio.get_event_loop().time()

        while (asyncio.get_event_loop().time() - start_time) < timeout_sec:
            # Checken ob der "Run" Button wieder erscheint und aktiv wird
            try:
                run_btn = self.page.locator("button").filter(has_text="Run").last
                if await run_btn.count() > 0 and await run_btn.is_enabled():
                    # Zusaetzlicher Puffer
                    await self.page.wait_for_timeout(3000)
                    break
            except:
                pass

            await self.page.wait_for_timeout(1000)

        print("[AIStudioController] Extrahiere Text per nativem Locator...")
        try:
            # Suche nach typischen Gemini-Textbausteinen
            chunks = await self.page.locator("ms-text-chunk, markdown-viewer, .model-turn").all()
            if chunks:
                text = await chunks[-1].inner_text()
            else:
                # Fallback: Letzter Paragraph der Seite
                paragraphs = await self.page.locator("p").all()
                text = await paragraphs[-1].inner_text() if paragraphs else "Kein Text gefunden."

            # UI-Knöpfe aus dem Text wischen
            for bad_word in ["content_copy", "expand_less", "Markdown", "download", "Copy code"]:
                text = text.replace(bad_word, "")

            result = text.strip()
            print(f"[AIStudioController] Erfolgreich extrahiert ({len(result)} Zeichen).")
            return result
        except Exception as e:
            print(f"[AIStudioController] Fehler beim Scrapen: {e}")
            return "Fehler beim Lesen der Antwort."
