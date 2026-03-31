from playwright.async_api import Page, expect
import asyncio
import time
import re
import os

class AIStudioController:
    def __init__(self, page: Page, request_id: str = "N/A"):
        self.page = page
        self.request_id = request_id
        self.url = "https://aistudio.google.com/app/prompts/new_chat"

    def log_event(self, event_name: str, **kwargs):
        import json
        payload = {
            "event": event_name,
            "request_id": self.request_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **kwargs
        }
        print(f"[EVENT] {json.dumps(payload)}")

    async def init_session(self):
        self.log_event("SESSION_INIT_STARTED")
        await asyncio.sleep(1)

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

    async def ensure_fresh_chat(self):
        """Hard reset via direct URL navigation to ensure a stateless environment."""
        self.log_event("NEW_CHAT_REQUESTED", url=self.url)
        
        max_retries = 3
        for attempt in range(max_retries):
            try:
                print(f"[AIStudioController] Lade neuen Chat (Versuch {attempt+1}/{max_retries})...")
                await self.page.goto(self.url, wait_until="domcontentloaded", timeout=60000)
                await asyncio.sleep(3)

                # 0. Check for Login Screen
                if "accounts.google.com" in self.page.url or "signin" in self.page.url.lower():
                    print("[AIStudioController] 🔐 LOGIN ERFORDERLICH! Bitte im Browser anmelden.")
                    self.log_event("LOGIN_REQUIRED", url=self.page.url)
                    # Wir geben dem Nutzer 30 Sekunden zum reagieren, bevor wir aufgeben
                    for i in range(30):
                        if "aistudio.google.com" in self.page.url and "signin" not in self.page.url.lower():
                            print("[AIStudioController] Login erkannt, fahre fort...")
                            break
                        await asyncio.sleep(1)
                    else:
                        raise RuntimeError("Login bei Google erforderlich. Bitte im Browser-Fenster manuell anmelden!")

                # 1b. Crash/Restore/Popup Clicker (The "Door Opener")
                # Erweitert um "Welcome", "Dismiss all", "Get started"
                popups = ["Restore", "Dismiss", "Accept", "Got it", "Welcome", "Get started", "Not now", "Confirm"]
                for popup in popups:
                    try:
                        # Suche nach Buttons, die diesen Text enthalten (Case-Insensitive)
                        btn = self.page.get_by_role("button", name=re.compile(popup, re.I)).last
                        if await btn.count() > 0 and await btn.is_visible():
                            print(f"[AIStudioController] Schließe Popup: '{popup}'")
                            await btn.click(force=True)
                            self.log_event("POPUP_DISMISSED", text=popup)
                            await asyncio.sleep(1)
                    except: pass

                # 2. Hard Ready-Check: Wait for prompt-box to be interactive
                print("[AIStudioController] Warte auf Prompt-Box (Eingabebereich)...")
                prompt_box = self.page.locator("ms-prompt-box textarea").first
                try:
                    await prompt_box.wait_for(state="visible", timeout=30000)
                    # Ensure it's not disabled (AI Studio sometimes overlays while loading)
                    for i in range(40):
                        if await prompt_box.is_enabled():
                            print(f"[AIStudioController] Prompt-Box bereit (nach {i*0.5}s).")
                            break
                        if i % 10 == 0:
                            print("[AIStudioController] Prompt-Box ist noch gesperrt (Loading UI?)...")
                        await asyncio.sleep(0.5)
                    else:
                        print("[AIStudioController] Prompt-Box blieb gesperrt. Versuche Reload.")
                        raise RuntimeError("Prompt-Box locked.")
                except Exception as e:
                    self.log_event("READY_CHECK_FAILED", error=str(e))
                    print(f"[AIStudioController] Prompt-Box nicht gefunden/bereit: {e}")
                    raise RuntimeError("Prompt-Box not interactive after timeout.")

                # 3. Clean-Verify: Paranoiac DOM validation
                # Check for any visible chat turns or markdown results
                bad_selectors = ["ms-chat-turn", "markdown-viewer", ".model-turn", ".message-content", ".shared-prompt"]
                dirty_elements = 0
                
                # Warte bis zu 5s, ob alte Elemente verschwinden
                for i in range(10):
                    dirty_elements = 0
                    for sel in bad_selectors:
                        try:
                            locs = await self.page.locator(sel).all()
                            for loc in locs:
                                if await loc.is_visible():
                                    dirty_elements += 1
                        except: pass
                    
                    if dirty_elements == 0: break
                    if i % 2 == 0:
                        print(f"[AIStudioController] Warte auf leeren Chat ({dirty_elements} Elemente noch da)...")
                    await asyncio.sleep(0.5)
                
                # Check textarea specifically
                prompt_box = self.page.locator("ms-prompt-box textarea, textarea").last
                text_val = ""
                if await prompt_box.count() > 0:
                    try: text_val = await prompt_box.input_value()
                    except: pass
                
                if dirty_elements == 0 and (not text_val or text_val.strip() == ""):
                    self.log_event("NEW_CHAT_VERIFIED", status="CLEAN", attempt=attempt+1)
                    print("[AIStudioController] ✓ Chat ist sauber und bereit.")
                    return
                else:
                    self.log_event("NEW_CHAT_DIRTY", elements=dirty_elements, text_length=len(text_val or ""), attempt=attempt+1)
                    print(f"[AIStudioController] Chat noch 'schmutzig' ({dirty_elements} Elemente, Text: {len(text_val or '')}). Erzwinge Reload...")
                    await self.page.reload(wait_until="domcontentloaded")
                    await asyncio.sleep(5)
            except Exception as e:
                self.log_event("NEW_CHAT_ERROR", error=str(e), attempt=attempt+1)
                print(f"[AIStudioController] Fehler in ensure_fresh_chat (Versuch {attempt+1}): {e}")
                await asyncio.sleep(2)

        self.log_event("FATAL_STATE_DIRTY", action="HALT")
        raise RuntimeError("Unrecoverable State Dirty: Could not clear AI Studio session after 3 retries.")

    async def check_immediate_quota(self):
        """Fast check for quota banner right after loading."""
        try:
            all_text = (await self.page.locator("body").inner_text() or "").lower()
            if "reached your rate limit" in all_text or "exceeded quota" in all_text:
                self.log_event("QUOTA_FALLBACK_TRIGGERED", trigger="immediate_load")
                await self.set_model("Gemini 1.5 Flash")
                await asyncio.sleep(2)
        except Exception as e:
            self.log_event("QUOTA_CHECK_ERROR", error=str(e))
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

            # 2. Clear & Inject
            # AI Studio's contenteditable is very stubborn. 
            # Best approach: Select All, Delete, then force the inner text.
            await self.page.keyboard.press("Control+A")
            await asyncio.sleep(0.1)
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(0.2)
            
            # Fast text injection using Javascript onto the actual nested textarea/element
            print("[AIStudioController] Injiziere Prompt...")
            await self.page.evaluate(f"""(text) => {{
                // Find all potential input areas
                let el = document.activeElement;
                if (!el || (el.tagName !== 'TEXTAREA' && !el.isContentEditable)) {{
                    const textareas = document.querySelectorAll('ms-prompt-box textarea, [contenteditable="true"]');
                    el = textareas[textareas.length - 1]; 
                }}
                
                if (el) {{
                    if (el.isContentEditable) {{
                        el.textContent = text;
                    }} else {{
                        el.value = text;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    }}
                }}
            }}""", prompt)

            # 3. Final nudge: type a space to trigger React state update
            await asyncio.sleep(0.5)
            await prompt_box.focus()
            await self.page.keyboard.type(" ")
            
            # 3b. UI-Freeze Stabilizer (Massive Prompts > 20k)
            wait_time = 5.0 if len(prompt) > 20000 else 2.0
            print(f"[AIStudioController] Paste done. Warten {wait_time}s auf React-Stabilisierung...")
            await asyncio.sleep(wait_time)

            # 4. Wait for Run button to be enabled (Token counting can take time)
            run_btn = self.page.locator("ms-run-button button, button:has-text('Run')").last
            if await run_btn.count() > 0:
                print("[AIStudioController] Warte auf Run-Button (Token counting)...")
                # Wait up to 120s for Token counting on massive prompts
                try:
                    await run_btn.wait_for(state="visible", timeout=30000)
                    for i in range(240): # up to 120s (0.5s steps)
                        if await run_btn.is_enabled():
                            print(f"[AIStudioController] Run-Button bereit nach {i*0.5}s.")
                            break
                        if i % 20 == 0:
                            print("[AIStudioController] Token-Zähler läuft noch...")
                        await asyncio.sleep(0.5)
                except:
                    print("[AIStudioController] Run-Button nicht sichtbar/bereit. Versuche Control+Enter Fallback.")

                if await run_btn.is_enabled():
                    await run_btn.click(force=True)
                    print("[AIStudioController] Run-Button geklickt. Warte auf Start der Generierung...")
                    
                    # 4b. Smart-Check: Hat die Generierung gestartet?
                    # Erhöht auf 3s, da Thinking-Modelle länger zum Umschalten brauchen
                    await asyncio.sleep(3.0)
                    
                    # Prüfe auf Indikatoren für aktive Generierung
                    is_generating = await self.page.locator("ms-thought-chunk, .generating, ms-stop-button").count() > 0
                    
                    if is_generating:
                        print("[AIStudioController] ✓ Generierung/Denken läuft bereits.")
                    elif await run_btn.count() > 0:
                        try:
                            btn_text = await run_btn.inner_text()
                            if "Stop" in btn_text or "Cancel" in btn_text:
                                print("[AIStudioController] ✓ Generierung läuft (Stop-Button erkannt).")
                            elif await run_btn.is_enabled():
                                print("[AIStudioController] Button noch aktiv/Run. Versuche vorsichtigen zweiten Klick...")
                                self.log_event("RETRY_CLICK_TRIGGERED")
                                await run_btn.click(force=True)
                        except: pass
                else:
                    print("[AIStudioController] Run-Button blieb disabled. Control+Enter Fallback...")
                    await self.page.keyboard.press("Control+Enter")
            else:
                print("[AIStudioController] Kein Run-Button gefunden. Control+Enter.")
                await self.page.keyboard.press("Control+Enter")

            await asyncio.sleep(2)

        except Exception as e:
            print(f"[AIStudioController] Fehler beim Senden: {e}")

    async def wait_for_response(self, timeout_sec: int = 600) -> str:
        print("[AIStudioController] Warte auf Antwort (Deep Scan)...")
        await asyncio.sleep(15)

        UI_BLACKLIST   = ["append to prompt", "alt + enter", "edit title",
                          "content_copy", "share", "expand_less",
                          "select a turn", "jump to it", "expand to view",
                          "thumb_up", "thumb_down", "edit", "more_vert",
                          "thoughts", "chevron_right"]
        NOISE_KEYWORDS = ["save the prompt", "run", "model selection",
                          "feature request", "anywhere", "select a turn",
                          "jump to it", "reached your rate limit",
                          "quota", "try again later", "failed to generate"]

        def clean(text: str) -> str:
            # Remove timestamps like "Model 8:31 PM"
            text = re.sub(r'Model \d+:\d+\s*(?:AM|PM)', '', text, flags=re.I)
            lines = text.splitlines()
            return "\n".join(
                l for l in lines
                if not any(b in l.lower() for b in UI_BLACKLIST)
            ).strip()

        def is_good(text: str, current_prompt: str) -> bool:
            # Fortress: Point-Based Scorer
            pts = 0
            low = text.strip().lower()
            
            # --- Point 1: Basic Length ---
            if len(text.strip()) > 100: pts += 1
            if len(text.strip()) > 350: pts += 1
            
            # --- Point 2: Structure (Markdown) ---
            has_markdown = any(m in text for m in ["# ", "* ", "1. ", "## ", "- "])
            if has_markdown: pts += 1
            
            # --- Point 3: Code Blocks ---
            if "```" in text: pts += 1
            
            # --- NEGATIVE: Generation Errors ---
            CRITICAL_ERRORS = ["reached your rate limit", "quota exceeded", "failed to generate", "intensive task"]
            for kw in CRITICAL_ERRORS:
                if kw in low: return False

            # --- NEGATIVE: Jaccard Echo Detection (> 70% Overlap) ---
            p_words = set(re.findall(r'\w+', current_prompt.lower()))
            r_words = set(re.findall(r'\w+', text.lower()[:800])) # Limit scan for speed
            if r_words and len(p_words) > 5:
                overlap = len(p_words.intersection(r_words)) / len(p_words.union(r_words))
                if overlap > 0.70:
                    print(f"[is_good] Rejecting turn: Jaccard Echo detected ({overlap:.2f})")
                    return False

            # Threshold Check
            is_valid = pts >= 2
            if not is_valid:
                print(f"[is_good] Rejecting turn: Score {pts}/4 below threshold.")
            return is_valid

        FALLBACK_MODEL = "Gemini 3 Flash Preview"
        quota_fallback_done = False

        # --- CHAOS SCENARIO B: FORCED QUOTA FALLBACK ---
        forced_quota = os.getenv("CHAOS_QUOTA", "false").lower() == "true"
        
        try:
            max_attempts = 100
            for attempt in range(max_attempts):
                # --- CHAOS SCENARIO A: INDUCED TIMEOUT (> 600s) ---
                if os.getenv("CHAOS_TIMEOUT", "false").lower() == "true":
                    self.log_event("CHAOS_INJECTION", type="TIMEOUT_DELAY")
                    await asyncio.sleep(650)

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
                    if (("reached your rate limit" in all_text or "exceeded quota" in all_text) or forced_quota) and not quota_fallback_done:
                        quota_fallback_done = True
                        self.log_event("QUOTA_FALLBACK_TRIGGERED", trigger="polling" if not forced_quota else "chaos_b")
                        await self.page.keyboard.press("Escape")
                        await asyncio.sleep(2)
                        
                        # Stateless reset before fallback
                        await self.ensure_fresh_chat()
                        await self.set_model(FALLBACK_MODEL)
                        await asyncio.sleep(2)
                        
                        if self.last_prompt:
                            await self.send_prompt(self.last_prompt)
                            await asyncio.sleep(15)
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
                            self.log_event("SCRAPE_POLLING_INFO", turn=i, strategy="1B", length=len(cleaned), snippet=cleaned[:50].replace("\n", " "))
                            
                            if is_good(cleaned, self.last_prompt or ""):
                                self.log_event("SCRAPE_SUCCESS", strategy="1B", length=len(cleaned))
                                return cleaned
                except Exception as e:
                    err_msg = str(e)
                    print(f"[AIStudioController] Strategy 1 error: {err_msg}")
                    if "closed" in err_msg or "Protocol error" in err_msg:
                        raise e # Trigger Phoenix Protocol

                await asyncio.sleep(10.0)

            return "Fehler: KI-Antwort nach Timeout nicht gefunden (DOM-Polling)."

        except Exception as e:
            err_msg = str(e)
            if "closed" in err_msg or "Protocol error" in err_msg:
                raise e # Propagate to Worker-Loop for Phoenix Retry
            import traceback
            return f"Fehler beim Scrapen: {err_msg}\n{traceback.format_exc()}"

    def is_valid_response(self, text: str) -> bool:
        if not text or len(text.strip()) < 20:
            return False
        if hasattr(self, 'last_prompt') and self.last_prompt:
            lp = self.last_prompt.strip()[:100]
            if lp and lp in text:
                return False
        return True
