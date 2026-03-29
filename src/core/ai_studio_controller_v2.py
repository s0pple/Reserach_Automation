"""
Robust AI Studio Controller - NO hardcoded coordinates
Uses Playwright locators for reliable cross-platform automation
"""
from typing import Optional
from playwright.async_api import Page
import asyncio
import time


class AIStudioController:
    """Robust browser automation for Google AI Studio using locators (no coordinates)."""
    
    def __init__(self, page: Page):
        self.page = page
        self.url = "https://aistudio.google.com/app/prompts/new_chat"
        self.turn_count_before = 0

    async def init_session(self):
        """Initialize session and dismiss banners."""
        print("[AIStudioController] Navigiere zu AI Studio...")
        await self.page.goto(self.url, wait_until="domcontentloaded")
        await asyncio.sleep(3)
        try:
            # Cookie Banner wegklicken
            await self.page.get_by_role("button", name="Agree").click(timeout=2000)
        except:
            pass
        print("[AIStudioController] ✓ Session initialized")

    async def set_model(self, model_name: str):
        """Change model using locators (NO hardcoded coordinates)."""
        print(f"[AIStudioController] Setze Modell auf: {model_name}")
        try:
            # STRATEGY 1: Find model dropdown button by looking for button containing current model text
            print("[AIStudioController]   [1/3] Versuche: Klicke Model-Dropdown-Button...")
            dropdown_btn = self.page.locator("button").filter(has_text="Gemini")
            if await dropdown_btn.count() > 0:
                await dropdown_btn.first.click(timeout=2000)
                print("[AIStudioController]       ✓ Model dropdown opened")
            else:
                # STRATEGY 2: Look for a button with role="combobox" (common pattern for dropdowns)
                print("[AIStudioController]   [2/3] Versuche: Combobox Locator...")
                combobox = self.page.locator("button[role='combobox']").first
                if await combobox.count() > 0:
                    await combobox.click(timeout=2000)
                    print("[AIStudioController]       ✓ Combobox opened")
                else:
                    # STRATEGY 3: Search for any button with text content suggesting it's a model selector
                    print("[AIStudioController]   [3/3] Versuche: Generic button search...")
                    buttons = await self.page.locator("button").all()
                    for btn in buttons:
                        text = await btn.text_content()
                        if text and ("Gemini" in text or "Flash" in text or "Pro" in text):
                            await btn.click(timeout=2000)
                            print(f"[AIStudioController]       ✓ Found and clicked: {text.strip()}")
                            break
            
            await asyncio.sleep(1)
            
            # Now select the model from the dropdown
            print("[AIStudioController]   Searching for model option in dropdown...")
            selected = False
            for test_name in [model_name, "Gemini 3 Flash", "Gemini 2.5 Flash", "Gemini 1.5 Pro"]:
                try:
                    option = self.page.locator("div, span").filter(has_text=test_name).first
                    if await option.count() > 0:
                        await option.click(timeout=1000)
                        print(f"[AIStudioController]   ✓ Model '{test_name}' selected!")
                        selected = True
                        break
                except:
                    pass
            
            if not selected:
                print("[AIStudioController]   ⚠ Model selection failed, but continuing...")
                
        except Exception as e:
            print(f"[AIStudioController] ⚠ Model change error: {e}")

    async def send_prompt(self, prompt: str):
        """Send prompt with robust error handling (no coordinate clicks)."""
        print(f"[AIStudioController] Sende Prompt ({len(prompt)} chars)...")
        try:
            # Find prompt textarea (always the last one)
            prompt_box = self.page.locator("textarea").last
            
            # Step 1: Focus and verify
            print("[AIStudioController]   [1/4] Focus textarea...")
            await prompt_box.focus()
            await asyncio.sleep(0.2)
            
            # Step 2: Fill text
            print("[AIStudioController]   [2/4] Fill text...")
            await prompt_box.fill(prompt)
            await asyncio.sleep(0.3)
            
            # Step 3: Trigger React state via keystroke
            print("[AIStudioController]   [3/4] Trigger SPA state (keystroke)...")
            await self.page.keyboard.type(" ")
            await asyncio.sleep(1.0)  # Allow React to update
            await self.page.keyboard.press("Backspace")
            await asyncio.sleep(0.3)
            
            # Record baseline turn count
            self.turn_count_before = await self.page.locator(".model-turn").count()
            print(f"[AIStudioController]       Turn count before: {self.turn_count_before}")
            
            # Step 4: Submit with robust fallbacks
            print("[AIStudioController]   [4/4] Submit (multi-fallback)...")
            submitted = False
            
            # ATTEMPT 1: Click Run button by text (most reliable)
            try:
                run_btn = self.page.locator("button").filter(has_text="Run").last
                if await run_btn.is_visible() and await run_btn.is_enabled():
                    await run_btn.click(force=True, timeout=3000)
                    print("[AIStudioController]       ✓ Run-Button clicked (text-based)")
                    submitted = True
            except Exception as e1:
                print(f"[AIStudioController]       ✗ Attempt 1 failed: {str(e1)[:50]}")
            
            # ATTEMPT 2: Click via aria-label (accessibility)
            if not submitted:
                try:
                    run_btn = self.page.locator("button[aria-label*='run' i]").last
                    if await run_btn.is_visible():
                        await run_btn.click(force=True, timeout=3000)
                        print("[AIStudioController]       ✓ Run-Button clicked (aria-label)")
                        submitted = True
                except Exception as e2:
                    print(f"[AIStudioController]       ✗ Attempt 2 failed: {str(e2)[:50]}")
            
            # ATTEMPT 3: Keyboard shortcut
            if not submitted:
                try:
                    await prompt_box.focus()
                    await asyncio.sleep(0.1)
                    await self.page.keyboard.press("Control+Enter")
                    print("[AIStudioController]       ✓ Control+Enter sent")
                    submitted = True
                except Exception as e3:
                    print(f"[AIStudioController]       ✗ Attempt 3 failed: {str(e3)[:50]}")
            
            if submitted:
                print("[AIStudioController] ✓ Submission successful")
            else:
                print("[AIStudioController] ⚠ All submission attempts failed!")
                
        except Exception as e:
            print(f"[AIStudioController] ❌ Error in send_prompt: {e}")

    async def wait_for_response(self, timeout_sec: int = 90) -> str:
        """Wait for AI response with robust polling."""
        print("[AIStudioController] Warte auf KI-Generierung...")
        start_time = time.time()
        
        # Wait for generation to start and complete
        await asyncio.sleep(10)  # Minimum wait for large prompts
        
        print("[AIStudioController] Suche nach dem Antwort-Element...")
        try:
            # Primary locator for AI responses
            locator = self.page.locator(".model-turn").last
            
            # Retry loop with progressive waiting
            for attempt in range(10):
                elapsed = time.time() - start_time
                if elapsed > timeout_sec:
                    break
                    
                current_count = await self.page.locator(".model-turn").count()
                if current_count > self.turn_count_before:
                    # New response detected, extract text
                    raw_text = await locator.text_content()
                    if raw_text and len(raw_text.strip()) > 10:
                        print(f"[AIStudioController] ✓ Response detected at attempt {attempt+1}")
                        break
                
                await asyncio.sleep(2)
            
            # Extract final text
            if await self.page.locator(".model-turn").count() == 0:
                return "Fehler: Keine KI-Antwort gefunden (.model-turn nicht vorhanden)."
            
            locator = self.page.locator(".model-turn").last
            raw_text = await locator.text_content()
            
            # Clean up UI artifacts
            for word in ["content_copy", "expand_less", "Markdown", "download", "Copy code", "expand_more"]:
                raw_text = raw_text.replace(word, "")
            
            result = raw_text.strip()
            print(f"[AIStudioController] ✓ Extraktion erfolgreich ({len(result)} Zeichen)")
            return result
            
        except Exception as e:
            return f"Fehler beim Scrapen: {str(e)}"
