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
            model_button = self.page.locator("[data-test-id='model-name']").first
            if await model_button.count() == 0:
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

            # 3. Geduld + Verifikation via stabilem Model-Label
            await self.page.wait_for_timeout(2000)
            actual_text = (await self.page.locator("[data-test-id='model-name']").first.text_content()) or ""
            actual_text = actual_text.strip()
            print(f"[AIStudioController] Modell-Name nach Wechsel (data-test-id=model-name): '{actual_text}'")
            if not actual_text:
                print(f"[AIStudioController] Warnung: Konnte Modell-Namen nicht verifizieren. Aktuell: {actual_text}")

            print(f"[AIStudioController] Modell erfolgreich geändert zu {model_name} ({actual_text})")
        except Exception as e:
            print(f"[AIStudioController] Fehler in set_model: {e}")
    async def send_prompt(self, prompt: str):
        print(f"[AIStudioController] Sende Prompt ({len(prompt)} Zeichen)...")
        self.last_prompt = prompt
        try:
            # 1. Target the correct input area
            prompt_box = self.page.locator("ms-prompt-box textarea, textarea").last
            if await prompt_box.count() == 0:
                prompt_box = self.page.locator("[contenteditable='true']").last
            
            await prompt_box.click(force=True)
            await prompt_box.focus()
            await asyncio.sleep(0.5)

            # 2. Clear & Inject via Clipboard-Sim (very reliable for large texts)
            await self.page.keyboard.press("Control+a")
            await self.page.keyboard.press("Backspace")
            
            # Using evaluate to set value and dispatch 'input' - works across most frameworks
            await self.page.evaluate(f"""(text) => {{
                const el = document.activeElement;
                if (!el) return;
                const valueSetter = Object.getOwnPropertyDescriptor(el.__proto__, 'value')?.set;
                const prototype = Object.getPrototypeOf(el);
                const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value')?.set;
                if (valueSetter && valueSetter !== prototypeValueSetter) {{
                    valueSetter.call(el, text);
                }} else {{
                    el.value = text;
                }}
                el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                el.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}""", prompt)

            # 3. Final nudge: type a space
            await self.page.keyboard.type(" ")
            await asyncio.sleep(1)

            # 4. Wait for Run button to be enabled
            run_btn = self.page.locator("ms-run-button button, button:has-text('Run')").last
            if await run_btn.count() > 0:
                print("[AIStudioController] Warte auf Run-Button-Enable (Token counting)...")
                for _ in range(120): # up to 60s
                    if await run_btn.is_enabled(): break
                    await asyncio.sleep(0.5)
                
                if await run_btn.is_enabled():
                    await run_btn.click(force=True)
                    print("[AIStudioController] ms-run-button geklickt.")
                else:
                    print("[AIStudioController] Run-Button blieb disabled. Versuche Control+Enter.")
                    await self.page.keyboard.press("Control+Enter")
            else:
                await self.page.keyboard.press("Control+Enter")
                print("[AIStudioController] Run-Button nicht gefunden. Control+Enter gesendet.")

            await asyncio.sleep(2)

        except Exception as e:
            print(f"[AIStudioController] Fehler beim Senden: {e}")

    async def wait_for_response(self, timeout_sec: int = 600) -> str:
        print("[AIStudioController] Warte auf Antwort (Deep Scan)...")
        await asyncio.sleep(15)

        UI_BLACKLIST   = ["append to prompt", "alt + enter", "edit title",
                          "content_copy", "share", "expand_less",
                          "select a turn", "jump to it", "expand to view",
                          "thumb_up", "thumb_down", "edit", "more_vert"]
        NOISE_KEYWORDS = ["save the prompt", "run", "model selection",
                          "feature request", "anywhere", "select a turn",
                          "jump to it", "reached your rate limit",
                          "quota", "try again later", "failed to generate"]

        def clean(text: str) -> str:
            lines = text.splitlines()
            return "\n".join(
                l for l in lines
                if not any(b in l.lower() for b in UI_BLACKLIST)
            ).strip()

        def is_good(text: str, current_prompt: str) -> bool:
            if not text or len(text.strip()) < 30:
                return False
            low = text.strip().lower()
            for kw in NOISE_KEYWORDS:
                if kw in low:
                    return False
            # Filter matches to original prompt
            p_snippet = current_prompt.strip()[:100]
            if p_snippet and p_snippet in text:
                return False
            return True

        FALLBACK_MODEL = "Gemini 3 Flash Preview"
        quota_fallback_done = False

        try:
            max_attempts = 100
            for attempt in range(max_attempts):
                print(f"[AIStudioController] Polling attempt {attempt+1}/{max_attempts}...")

                # Frequent Debugging with expanded tag list
                if attempt < 3 or attempt % 5 == 0:
                    try:
                        probe_tags = ['ms-text-chunk', 'ms-chat-turn', 'ms-thought-chunk', 'p', "[role='alert']", "ms-prompt-chunk"]
                        for p in probe_tags:
                            n = await self.page.locator(p).count()
                            if n > 0:
                                last_txt = (await self.page.locator(p).last.inner_text() or "").strip().replace("\n", " [n] ")
                                print(f"[DOM-DEBUG] {p:20s} count={n:3d} last[:60]={last_txt[:60]!r}")
                    except Exception: pass

                # --- QUOTA DETECTION ---
                try:
                    all_text = (await self.page.locator("body").inner_text() or "").lower()
                    if ("reached your rate limit" in all_text or "exceeded quota" in all_text) and not quota_fallback_done:
                        quota_fallback_done = True
                        print(f"[⚠️ QUOTA] Rate-limit! Switching to {FALLBACK_MODEL}...")
                        await self.page.keyboard.press("Escape")
                        await asyncio.sleep(2)
                        await self.set_model(FALLBACK_MODEL)
                        await asyncio.sleep(5)
                        if self.last_prompt:
                            await self.send_prompt(self.last_prompt)
                            await asyncio.sleep(20)
                        continue
                except Exception: pass

                # --- Strategy 1: turn.inner_text() (Modern Clean Fallback) ---
                try:
                    turns = await self.page.locator("ms-chat-turn").all()
                    if len(turns) >= 2:
                        for i in range(len(turns)-1, 0, -1):
                            turn = turns[i]
                            html = await turn.inner_html()
                            if "loading" in html.lower() or "spinner" in html.lower():
                                print(f"[AIStudioController] Turn {i} currently loading...")
                                break 
                            
                            # Method A: text-chunks
                            chunks = await turn.locator("ms-text-chunk").all()
                            if chunks:
                                combined = "\n".join([await c.inner_text() for c in chunks])
                                cleaned = clean(combined)
                                if is_good(cleaned, self.last_prompt or ""):
                                    print(f"[AIStudioController] ✓ Found via Strategy 1A (chunks) in turn {i}, length={len(cleaned)}")
                                    return cleaned
                            
                            # Method B: raw inner text (fallback for tricky turns)
                            raw = await turn.inner_text()
                            cleaned = clean(raw)
                            if is_good(cleaned, self.last_prompt or ""):
                                print(f"[AIStudioController] ✓ Found via Strategy 1B (inner_text) in turn {i}, length={len(cleaned)}")
                                return cleaned
                except Exception as e:
                    print(f"[AIStudioController] Strategy 1 error: {e}")

                await asyncio.sleep(10.0)

            return "Fehler: KI-Antwort nach Timeout nicht gefunden (DOM-Polling)."

        except Exception as e:
            import traceback
            return f"Fehler beim Scrapen: {e}\n{traceback.format_exc()}"

    def _is_valid_response(self, text: str) -> bool:
        if not text or len(text.strip()) < 20:
            return False
        return True

    def _is_valid_response(self, text: str) -> bool:
        if not text or len(text.strip()) < 20:
            return False
        if hasattr(self, 'last_prompt') and self.last_prompt:
            lp = self.last_prompt.strip()
            if lp and lp in text:
                return False
        return True
