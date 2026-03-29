from playwright.async_api import Page, expect
import asyncio
import time
import re

class AIStudioController:
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://aistudio.google.com/app/prompts/new_chat"

    async def init_session(self):
        print("[AIStudioController] Navigiere zu AI Studio...")
        await self.page.goto(self.url, wait_until="networkidle")
        await asyncio.sleep(5)

        # 0. Optional: Seitenleiste schließen, falls angezeigt
        try:
            print("[AIStudioController] Versuche Seitenleiste zu schließen...")
            await self.page.keyboard.press("Control+Shift+L")
            await asyncio.sleep(1)
            # Fallback: Hamburger-Menü suchen und klicken
            hamburger = self.page.get_by_role("button", name=re.compile("menu|hamburger|sidebar", re.I)).first
            if await hamburger.count() and await hamburger.is_visible():
                await hamburger.click(force=True)
                print("[AIStudioController] Hamburger-Menü geklickt (Seitenleiste geschlossen).")
                await asyncio.sleep(1)
        except Exception as e:
            print(f"[AIStudioController] Seitenleiste schließen fehlgeschlagen: {e}")

    async def set_model(self, model_name: str):
        print(f"[AIStudioController] Setze Modell auf: {model_name}")
        try:
            # 1. Open dropdown by known model selector button patterns
            model_button = self.page.locator("button-model-selector, .model-selector-button, [aria-haspopup='listbox']").first
            if await model_button.count() == 0:
                model_button = self.page.locator("button").filter(has_text=re.compile("Gemini", re.I)).first

            if await model_button.count() == 0:
                raise RuntimeError("Kein Modell-Dropdown-Button gefunden")

            await model_button.click(force=True)
            await asyncio.sleep(1)

            # 2. Select exact model
            choice = self.page.get_by_text(model_name).first
            if await choice.count() == 0:
                raise RuntimeError(f"Modell '{model_name}' nicht gefunden")
            await choice.click(force=True)
            await asyncio.sleep(1)

            # 3. Geduld + dynamische Re-Lookup-Verifikation
            await self.page.wait_for_timeout(2000)
            updated_button = self.page.locator("button-model-selector, .model-selector-button, [aria-haspopup='listbox']").first
            html = await updated_button.inner_html()
            print(f"[DEBUG] Model-Button HTML: {html}")
            await self.page.screenshot(path="temp/debug_model_selector.png")
            actual_text = (await updated_button.inner_text()) or ""
            print(f"[AIStudioController] Modell-Button Text nach Wechsel (inner_text): '{actual_text}'")
            if "flash" not in actual_text.lower():
                raise RuntimeError(f"Modellwechsel fehlgeschlagen (Flash nicht im Text): {actual_text}")

            print(f"[AIStudioController] Modell erfolgreich geändert zu {model_name} ({actual_text})")
        except Exception as e:
            print(f"[AIStudioController] Fehler in set_model: {e}")
            try:
                fallback_button = self.page.locator("button-model-selector, .model-selector-button, [aria-haspopup='listbox']").first
                if await fallback_button.count() > 0:
                    dump_html = await fallback_button.inner_html()
                    print(f"[DEBUG][EXCEPT] Fallback Model-Button HTML: {dump_html}")
                else:
                    print("[DEBUG][EXCEPT] Kein Fallback Model-Button gefunden")

                await self.page.screenshot(path="temp/debug_model_selector_error.png")
                full_content = await self.page.content()
                with open("temp/debug_model_full_page.html", "w", encoding="utf-8") as f:
                    f.write(full_content)
                print("[DEBUG][EXCEPT] Screenshot + full-page HTML gespeichert unter temp/")
            except Exception as dumperr:
                print(f"[DEBUG][EXCEPT] Diagnostic dump fehlgeschlagen: {dumperr}")
            raise
    async def send_prompt(self, prompt: str):
        print("[AIStudioController] Sende Prompt (Hard Send)...")
        self.last_prompt = prompt
        try:
            # 1. Textfeld finden, klicken, befüllen
            prompt_box = self.page.locator("textarea").last
            await prompt_box.click(force=True)
            await prompt_box.fill(prompt)

            # 2. Space-Trick ausführen
            await self.page.keyboard.type(" ")
            await asyncio.sleep(1)

            # 3. Submission-Kaskade
            await self.page.keyboard.press("Control+Enter")
            print("[AIStudioController] Control+Enter gesendet.")
            await asyncio.sleep(2)

            run_btn = self.page.get_by_role("button", name=re.compile("run", re.I)).last
            if await run_btn.is_visible():
                if await run_btn.is_enabled():
                    await run_btn.click(force=True)
                    print("[AIStudioController] Run-Button geklickt (force).")
                else:
                    print("[AIStudioController] Run-Button nicht enabled trotz Control+Enter.")
            else:
                print("[AIStudioController] Run-Button nicht sichtbar nach Control+Enter.")

        except Exception as e:
            print(f"[AIStudioController] Fehler beim Senden: {e}")

    async def wait_for_response(self, timeout_sec: int = 90) -> str:
        print("[AIStudioController] Warte auf Antwort (Deep Scan)...")
        await asyncio.sleep(15)

        blacklist = [
            "save the prompt",
            "share",
            "run",
            "model selection",
            "feature request",
            "anywhere"  # fallback noise words
        ]

        def is_noise(text: str):
            normalized = text.strip().lower()
            if len(normalized) < 40:
                return True
            for noise in blacklist:
                if noise in normalized:
                    return True
            return False

        selectors = [
            "main .model-turn, .chat-content .model-turn",
            "section.chat-history div[role='log'] .model-turn",
            ".model-turn"
        ]

        try:
            for sel in selectors:
                nodes = await self.page.locator(sel).all()
                print(f"[AIStudioController] Check selector '{sel}': {len(nodes)} nodes")
                if nodes:
                    candidate_text = await nodes[-1].text_content()
                    if candidate_text:
                        clean_text = candidate_text.replace("content_copy", "").replace("expand_less", "").strip()
                        if not is_noise(clean_text) and self._is_valid_response(clean_text):
                            print(f"[AIStudioController] Antwort gefunden via '{sel}', length={len(clean_text)}")
                            return clean_text

            # Fallback: Suche in bekannten container-Strukturen per Playwright-API (kein evaluate-Block)
            for container_sel in ["main", ".chat-content", "section.chat-history"]:
                cont = self.page.locator(container_sel).first
                if await cont.count() > 0:
                    text_blob = await cont.text_content() or ""
                    lines = [x.strip() for x in text_blob.split("\n") if x.strip()]
                    candidates = [x for x in lines if not is_noise(x) and self._is_valid_response(x)]
                    if candidates:
                        raw = candidates[-1].strip()
                        print(f"[AIStudioController] Antwort gefunden via Container '{container_sel}'")
                        return raw

            # Letzter Reserve-Fallback: ganzer Body-Text
            body_text = await self.page.text_content("body") or ""
            lines = [x.strip() for x in body_text.split("\n") if x.strip()]
            candidates = [x for x in lines if not is_noise(x) and self._is_valid_response(x)]
            if candidates:
                raw = candidates[-1].strip()
                print("[AIStudioController] Antwort gefunden via body text fallback")
                return raw

            return "Fehler: KI-Antwort im HTML nicht identifizierbar."

        except Exception as e:
            return f"Fehler beim Scrapen: {e}"

    def _is_valid_response(self, text: str) -> bool:
        if not text or len(text.strip()) < 20:
            return False

        if hasattr(self, 'last_prompt') and self.last_prompt:
            lp = self.last_prompt.strip()
            if lp and lp in text:
                return False

        return True
