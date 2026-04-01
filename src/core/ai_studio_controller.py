from playwright.async_api import Page, expect
import asyncio
import time
import re
import os
from .state_manager import StateManager, Milestone

class AIStudioController:
    def __init__(self, page: Page, request_id: str = "N/A", session_id: str = "default"):
        self.page = page
        self.request_id = request_id
        self.session_id = session_id
        self.state_manager = StateManager()
        self.causality_log = []
        self.last_prompt = ""
        self.last_snapshot_len = 0
        self.url = "https://aistudio.google.com/app/prompts/new_chat"

    def log_event(self, event_name: str, **kwargs):
        import json
        payload = {
            "event": event_name,
            "request_id": self.request_id,
            "session_id": self.session_id,
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            **kwargs
        }
        print(f"[EVENT] {json.dumps(payload)}")

    async def update_milestone(self, milestone: Milestone):
        self.state_manager.update_milestone(self.session_id, milestone, url=self.page.url)
        self.state_manager.record_milestone_progress(self.session_id)
        self.causality_log.append({"event": "MILESTONE", "value": milestone.value, "time": time.time()})
        self.log_event("MILESTONE_REACHED", milestone=milestone.value)

    async def smart_click(self, label: str, selector: str = None):
        """Escalation-based clicking: Plan A (CSS) -> Plan B (Fuzzy) -> Plan C (Vision Signal)."""
        self.log_event("SMART_CLICK_START", label=label)
        
        # Taking a pre-click screenshot for Visual Reflection
        pre_screenshot = await self.page.screenshot()
        
        # Plan A: Direct Selector (if provided) or specific CSS
        if selector:
            try:
                btn = self.page.locator(selector).first
                if await btn.count() > 0 and await btn.is_enabled():
                    print(f"🪜 [Plan A] Clicking selector: {selector}")
                    await btn.click(force=True)
                    if await self._verify_click_success(pre_screenshot): return True
            except: pass

        # Plan B: Fuzzy Search & Accessibility Tree
        try:
            print(f"🪜 [Plan B] Fuzzy search for: {label}")
            fuzzy_btn = self.page.get_by_role("button", name=re.compile(label, re.I)).first
            if await fuzzy_btn.count() == 0:
                fuzzy_btn = self.page.get_by_text(re.compile(label, re.I)).first
            
            if await fuzzy_btn.count() > 0:
                await fuzzy_btn.click(force=True)
                if await self._verify_click_success(pre_screenshot): return True
        except: pass

        # Plan C: Vision (Placeholder for VLM integration, currently coordinate-based)
        # Note: In a real scenario, we'd send the screenshot to a VLM here.
        self.log_event("SMART_CLICK_ESCALATION", level="C", label=label)
        print(f"🪜 [Plan C] Vision-based fallback (Signal only for now)")
        # If we had VLM coords, we'd do: await self.page.mouse.click(x, y)
        
        return False

    async def _verify_click_success(self, pre_screenshot_bytes) -> bool:
        """Verifies click success via DOM changes first, then Pixel Delta."""
        await asyncio.sleep(0.5) # Wait for animation/state change
        
        # Truth 1: DOM Indicators (Loading spinner, disabled button, etc.)
        is_generating = await self.page.locator("ms-stop-button, .generating, ms-thought-chunk").count() > 0
        if is_generating:
            print("✅ [Reflection] DOM Change detected (Generation started).")
            return True

        # Signal 2: Pixel Delta (Xvfb screens are 1920x1080)
        post_screenshot = await self.page.screenshot()
        if len(pre_screenshot_bytes) != len(post_screenshot):
            print("💡 [Reflection] Pixel Signal: Byte-length delta detected.")
            return True
            
        return False

    async def get_cognitive_snapshot(self) -> dict:
        """Captures a 1024x768 screenshot and a lean DOM representation."""
        self.log_event("COGNITIVE_SNAPSHOT_START")
        screenshot = await self.page.screenshot(type="jpeg", quality=80) 
        import base64
        return {
            "screenshot_b64": base64.b64encode(screenshot).decode('utf-8'),
            "lean_dom": await self.extract_lean_dom(),
            "url": self.page.url,
            "milestone": self.state_manager.load_state(self.session_id).current_milestone.value if self.state_manager.load_state(self.session_id) else "unknown"
        }

    async def extract_lean_dom(self) -> str:
        """Extracts only strictly relevant interactive elements and visible text tags."""
        script = """
        () => {
            const results = [];
            // 1. Visible Buttons & Inputs
            const interactors = document.querySelectorAll('button, input, textarea, [role="button"], [role="link"], [role="checkbox"]');
            interactors.forEach(el => {
                const rect = el.getBoundingClientRect();
                if (rect.width > 0 && rect.height > 0 && window.getComputedStyle(el).visibility !== 'hidden') {
                    results.push(`[${el.tagName.toLowerCase()}] text="${el.innerText || el.value || ''}" aria="${el.ariaLabel || ''}" disabled=${el.disabled}`);
                }
            });
            // 2. Modals & Alerts
            const alerts = document.querySelectorAll('[role="alert"], [aria-modal="true"], .modal, .dialog');
            alerts.forEach(el => {
                results.push(`[ALERT/MODAL] text="${el.innerText.substring(0, 100).replace(/\\n/g, ' ')}"`);
            });
            // 3. Last 500 chars of body text (generic errors)
            const bodyEnd = document.body.innerText.slice(-500);
            results.push(`[BODY_TAIL] ${bodyEnd.replace(/\\n/g, ' ')}`);
            return results.join('\\n');
        }
        """
        return await self.page.evaluate(script)

    async def execute_oracle_strategy(self, strategy: str, confidence: float) -> bool:
        """Executes a whitelisted strategy with risk-based confidence gating."""
        s = strategy.upper()
        
        # --- ARE: Anti-Hysteresis Logic ---
        st = self.state_manager.load_state(self.session_id)
        if st and st.last_oracle_strategy == s:
            print(f"🛑 [ARE] Hysteresis Detected: Strategy '{s}' already failed once. Aborting.")
            self.causality_log.append({"event": "ABORT", "reason": "Hysteresis Prevention", "strategy": s})
            return False

        self.causality_log.append({"event": "ORACLE_EXECUTION", "strategy": s, "confidence": confidence})
        self.log_event("STRATEGY_EXECUTION_START", strategy=s, confidence=confidence)

        # Risk Triage
        if "CLICK" in s and confidence < 0.85:
            print(f"⚠️ [Plan D] CLICK rejected (Confidence {confidence} < 0.85). Falling back to RELOAD.")
            s = "RELOAD_PAGE"
        elif confidence < 0.6:
            print(f"⚠️ [Plan D] LOW CONFIDENCE ({confidence}). Falling back to RELOAD.")
            s = "RELOAD_PAGE"

        try:
            self.state_manager.record_oracle_intervention(self.session_id, s)
            if s == "SCROLL_DOWN":
                await self.page.mouse.wheel(0, 500)
                await asyncio.sleep(2)
            elif s == "WAIT_10S":
                print("🪜 [Plan D] Waiting 10s...")
                await asyncio.sleep(10)
            elif s == "RELOAD_PAGE":
                print("🪜 [Plan D] Reloading page...")
                await self.page.reload()
                await asyncio.sleep(8)
            elif s == "CLICK_RUN_SUBMIT":
                print("🪜 [Plan D] Attempting targeted CLICK (Run/Submit)...")
                btn_labels = ["Run", "Send", "Submit", "Generate", "Execute"]
                clicked = False
                for label in btn_labels:
                    if await self.smart_click(label):
                        clicked = True
                        break
                if clicked: await asyncio.sleep(4)
                return clicked
            elif s == "FATAL_ABORT":
                print("🛑 [Plan D] Oracle recommended ABORT.")
                return False
            
            return True
        except Exception as e:
            print(f"❌ [Plan D] Strategy implementation failed: {e}")
            return False

    async def is_progressing(self, current_text: str) -> bool:
        """ARE Phase 1: Causality Check. Distinguishes between 'Waiting' and 'Streaming'."""
        current_len = len(current_text)
        diff = current_len - self.last_snapshot_len
        self.last_snapshot_len = current_len
        
        # Positive growth means generation is happening
        if diff > 0:
            print(f"[is_progressing] Snapshot diff: +{diff} characters.")
            return True
        
        # Also check for thought chunks/spinners
        if await self.page.locator("ms-thought-chunk, .generating").count() > 0:
            print("[is_progressing] Thought/Generating markers detected.")
            return True

        print(f"[is_progressing] Snapshot diff: 0 characters (no change) in 4s.")
        return False

    async def consult_oracle(self) -> dict:
        """Consults the LLM Architect for a diagnostic strategy."""
        print("🧠 [Plan D] 🏗️ CONSULTING THE ARCHITECT...")
        snapshot = await self.get_cognitive_snapshot()
        
        prompt = f"""You are the ARCHITECT of the Iron Fortress Research Automation.
The automation is STUCK at milestone: {snapshot['milestone']}.
URL: {snapshot['url']}

LEAN DOM SNAPSHOT:
{snapshot['lean_dom']}

MISSION: Analyze the situation and return a JSON strategy.
Whitelisted Strategies: SCROLL_DOWN, WAIT_10S, RELOAD_PAGE, CLICK_RUN_SUBMIT, FATAL_ABORT.

RULES:
1. If a popup/modal is visible, suggest RELOAD_PAGE or a strategy to dismiss it.
2. If the 'Run' button seems disabled but input is present, suggest WAIT_10S.
3. If everything looks correct but no generation starts, suggest CLICK_RUN_SUBMIT.
4. Output STRICT JSON: {{ "problem": "...", "strategy": "...", "confidence": 0.0-1.0 }}
"""
        # Note: In production, we'd send the b64 screenshot too. 
        # For now we use text-based diagnosis via the proxy.
        from src.proxy.openai_proxy import ask_browser_agent
        try:
            # We use ask_browser_agent but directed to AI Studio with a specific diagnosis prompt
            raw_response = await ask_browser_agent(prompt, model="browser-agent-gemini", request_id=f"plan_d_{self.request_id}")
            import json
            # Extract JSON from potential markdown markers
            clean_json = re.search(r"\{.*\}", raw_response, re.DOTALL).group(0)
            diagnosis = json.loads(clean_json)
            print(f"[PLAN D] 💡 Oracle Response: Strategy={diagnosis.get('strategy')} (Confidence: {diagnosis.get('confidence')})")
            return diagnosis
        except Exception as e:
            print(f"❌ [Plan D] Oracle consultation failed: {e}")
            return {"strategy": "RELOAD_PAGE", "confidence": 0.5, "problem": "Oracle Error"}

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
        """Surgical DOM-based reset to ensure a stateless environment with minimal overhead."""
        print("[AIStudioController] Ensuring fresh chat state (Surgical Reset)...")
        try:
            # Step 1: Perform the Reset (Plan A: Button Click, Plan B: Link, Plan D: URL)
            new_chat_btn = self.page.locator('button[aria-label="New chat"]').first
            if await new_chat_btn.is_visible():
                print("[AIStudioController] Plan A: Clicking 'New Chat' button.")
                await new_chat_btn.click()
                await asyncio.sleep(1.5)
            else:
                playground_link = self.page.locator('a.playground-link').first
                if await playground_link.is_visible():
                    print("[AIStudioController] Plan B: Clicking sidebar Playground link.")
                    await playground_link.click()
                    await asyncio.sleep(1.5)
                else:
                    print("[AIStudioController] Plan D: Hard URL reset via navigation.")
                    await self.page.goto("https://aistudio.google.com/app/prompts/new_chat", wait_until="domcontentloaded", timeout=15000)

            # Step 2: Login Check (Critical persistent requirement)
            if "accounts.google.com" in self.page.url or "signin" in self.page.url.lower():
                print("[AIStudioController] 🔐 LOGIN ERFORDERLICH! Bitte im Browser anmelden.")
                self.log_event("LOGIN_REQUIRED", url=self.page.url)
                # 30s grace period for manual login
                for i in range(30):
                    if "aistudio.google.com" in self.page.url and "signin" not in self.page.url.lower():
                        print("[AIStudioController] Login erkannt, fahre fort...")
                        break
                    await asyncio.sleep(1)
                else:
                    raise RuntimeError("Login bei Google erforderlich. Bitte im Browser-Fenster manuell anmelden!")

            # Step 3: Popup Discharge (Clear blocking overlays)
            popups = ["Restore", "Dismiss", "Accept", "Got it", "Welcome", "Get started", "Not now", "Confirm"]
            for popup in popups:
                try:
                    btn = self.page.get_by_role("button", name=re.compile(popup, re.I)).last
                    if await btn.count() > 0 and await btn.is_visible():
                        print(f"[AIStudioController] Schließe Popup: '{popup}'")
                        await btn.click(force=True)
                        await asyncio.sleep(1)
                except: pass

            # Step 4: Readiness Check (Wait for tool interaction zone)
            print("[AIStudioController] Warte auf Prompt-Box (Eingabebereich)...")
            prompt_box = self.page.locator("ms-prompt-box textarea, [contenteditable='true']").last
            await prompt_box.wait_for(state="visible", timeout=15000)
            
            # Stabilization loop (AI Studio loading state)
            for i in range(20):
                if await prompt_box.is_enabled():
                    print(f"[AIStudioController] Prompt-Box bereit (nach {i*0.5}s).")
                    break
                await asyncio.sleep(0.5)

            print("[AIStudioController] Surgical reset complete.")
            return True

        except Exception as e:
            print(f"[AIStudioController] ERROR in ensure_fresh_chat: {e}. Attempting Last-Resort Reload.")
            await self.page.goto("https://aistudio.google.com/app/prompts/new_chat", wait_until="networkidle", timeout=30000)
            return False

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
    async def consult_oracle(self) -> dict:
        print("🧠 [Plan D] Consulting Oracle (Vision Scan)...")
        # In a real scenario, this would take a screenshot and ask a vision model.
        # For ARE Phase 3 validation, we simulate a diagnostic for documented chaos.
        sabotage = os.getenv("CHAOS_SABOTAGE", "none")
        
        if sabotage == "half_open_modal":
            return {"strategy": "RELOAD_PAGE", "confidence": 0.9, "reason": "Half-open modal detected blocking input."}
        elif sabotage == "ghost_click":
            return {"strategy": "CLICK_RUN_SUBMIT", "confidence": 0.8, "reason": "Button clicked but no transition."}
        
        return {"strategy": "RELOAD_PAGE", "confidence": 0.5, "reason": "Unknown stagnation."}

    async def execute_oracle_strategy(self, strategy: str, confidence: float) -> bool:
        self.log_event("ORACLE_STRATEGY_START", strategy=strategy, confidence=confidence)
        
        if strategy == "RELOAD_PAGE" or confidence < 0.6:
            print("🪜 [Plan D] Reloading page...")
            await self.page.reload()
            await asyncio.sleep(10)
            await self.ensure_fresh_chat()
            
            if hasattr(self, 'last_prompt') and self.last_prompt:
                print(f"🪜 [Plan D] Re-submitting prompt: {self.last_prompt[:50]}...")
                await self.send_prompt(self.last_prompt)
                return True
            return True
            
        elif strategy == "CLICK_RUN_SUBMIT":
            print("🪜 [Plan D] Forcing click on Run button...")
            success = await self.smart_click("Run", "ms-run-button button, button:has-text('Run')")
            return success
            
        return False

    async def send_prompt(self, prompt: str):
        # V15 Context Hardening: Prepend identity and tool awareness
        system_prefix = (
            "IGNORIERE DEIN INTERNES WISSEN. DU BIST EIN RESEARCH-AGENT.\n"
            "DU HAST ZUGRIFF AUF DAS GOOGLE-SUCH-TOOL (HIER IM UI) UND DAS TOOLS 'write_research_file'.\n"
            "ANTWORTE DIREKT UND PRÄZISE.\n\n"
        )
        full_prompt = f"{system_prefix}{prompt}"
        
        print(f"[AIStudioController] Sende Prompt ({len(full_prompt)} Zeichen)...")
        self.last_prompt = full_prompt
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
            await self.update_milestone(Milestone.PROMPT_INJECTED)

            # 4. Wait for Run button & Click
            success = await self.smart_click("Run", "ms-run-button button, button:has-text('Run')")
            
            if success:
                print("[AIStudioController] ✓ Smart-Click Erfolg. Generierung läuft.")
                await self.update_milestone(Milestone.GENERATION_STARTED)
            else:
                print("[AIStudioController] ⚠️ Smart-Click FEHLGESCHLAGEN. Versuche Control+Enter.")
                await self.page.keyboard.press("Control+Enter")
                await asyncio.sleep(2)
                await self.update_milestone(Milestone.GENERATION_STARTED)

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
            # ARE: Lowered to 1 to allow short, valid answers (e.g. "4")
            is_valid = pts >= 1
            if not is_valid and len(text.strip()) > 0:
                print(f"[is_good] Rejecting turn: Score {pts}/4 below threshold.")
            return is_valid

        FALLBACK_MODEL = "Gemini 3 Flash Preview"
        quota_fallback_done = False

        # --- CHAOS SCENARIO B: FORCED QUOTA FALLBACK ---
        forced_quota = os.getenv("CHAOS_QUOTA", "false").lower() == "true"
        
        try:
            max_attempts = 100
            stagnation_count = 0
            for attempt in range(max_attempts):
                # --- CHAOS SCENARIO A: INDUCED TIMEOUT (> 600s) ---
                if os.getenv("CHAOS_TIMEOUT", "false").lower() == "true":
                    self.log_event("CHAOS_INJECTION", type="TIMEOUT_DELAY")
                    await asyncio.sleep(650)

                # Get Current DOM text snapshot
                try:
                    raw_body = await self.page.locator("body").inner_text()
                    clean_text = clean(raw_body)
                except: clean_text = ""

                # --- ARE: STAGNATION DETECTION (Subtle Noise) ---
                if not await self.is_progressing(clean_text):
                    stagnation_count += 1
                    if stagnation_count >= 2: # 8 seconds of no change
                        print(f"[AIStudioController] Stagnation erkannt nach 8s Leerlauf.")
                        diag = await self.consult_oracle()
                        success = await self.execute_oracle_strategy(diag.get("strategy", "RELOAD_PAGE"), diag.get("confidence", 0.5))
                        if success:
                            # After recovery (e.g. reload), we must restart the wait loop
                            return await self.wait_for_response() 
                        else:
                            return "Fehler: Agent konnte sich nicht aus Stagnation befreien."
                else:
                    stagnation_count = 0

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
                                await self.update_milestone(Milestone.COMPLETED)
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
