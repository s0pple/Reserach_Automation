import logging
import asyncio
import os
import mss
import io
import numpy as np
import cv2
from PIL import Image
from telegram import Bot
from typing import Dict, Any, Callable, Awaitable
from src.agents.general_agent.planner import PlanningAgent
from src.tools.cv_bot.cv_bot_tool import CVBotTool

logger = logging.getLogger(__name__)

class GeneralExecutor:
    """
    The Reason-Act-Observe Loop for the General Agent.
    Now supports persistent sessions and auto-screenshots.
    """
    def __init__(self):
        self.planner = PlanningAgent()
        self.max_retries = 3
        self.cv_tool = CVBotTool()
        self.persistent_context_path = "/app/browser_sessions/general_agent"

    async def _send_telegram_photo(self, telegram_callback, caption=""):
        """Helper to take a screenshot and send it via the callback if possible."""
        if not telegram_callback: return
        
        try:
            # We assume telegram_callback can handle text. 
            # But the bot architecture passes a wrapper that calls bot.send_message.
            # We need to hack access to the bot or use a separate screenshot sender.
            # Ideally, we save to disk and tell the user to use /watch, OR we implement a photo sender.
            
            # Since we can't easily pass the bot object down here in the current architecture without refactoring,
            # we will take a screenshot to a known path and tell the user.
            
            # BETTER: We use the TOKEN from env and send it directly.
            token = os.getenv("TELEGRAM_BOT_TOKEN")
            chat_id = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "").split(",")[0]
            
            if token and chat_id:
                path = f"temp/gen_agent_{int(asyncio.get_event_loop().time())}.png"
                os.makedirs("temp", exist_ok=True)
                os.system(f"export DISPLAY=:99 && scrot -z {path}")
                
                if os.path.exists(path):
                    bot = Bot(token=token)
                    with open(path, "rb") as f:
                        await bot.send_photo(chat_id=chat_id, photo=f, caption=caption)
                    os.remove(path)
        except Exception as e:
            logger.error(f"Failed to send photo: {e}")

    async def run(self, goal: str, initial_state: Dict[str, Any], telegram_callback: Callable[[str], Awaitable[None]] = None) -> Dict[str, Any]:
        """
        Runs the dynamic loop until the goal is achieved or max retries are hit.
        """
        from playwright.async_api import async_playwright
        
        # Make sure Playwright renders in the Xvfb virtual monitor so /live sees it
        os.environ["DISPLAY"] = ":99"
        
        current_state = initial_state.copy()
        step_count = 0
        consecutive_failures = 0
        
        logger.info("[Executor] Starting Persistent Playwright in Xvfb...")
        if telegram_callback:
            await telegram_callback("🔄 Starte persistenten Browser (Session wird gespeichert)...")
            
        async with async_playwright() as p:
            # Launch PERSISTENT context so cookies/login are saved and browser stays open if we want
            # Note: launch_persistent_context does not support 'browser.close()' the same way.
            # We must use context.close() at the end.
            
            args = ["--no-sandbox", "--disable-dev-shm-usage", "--disable-blink-features=AutomationControlled"]
            
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.persistent_context_path,
                headless=False, # Important for Xvfb
                args=args,
                viewport={'width': 1920, 'height': 1080}
            )
            
            page = context.pages[0] if context.pages else await context.new_page()
            
            while step_count < 10:
                step_count += 1
                
                # Fetch current URL for context
                current_state["url"] = page.url
                
                # Capture Screenshot for Planner
                screenshot_bytes = await page.screenshot(type="jpeg", quality=70) # Compress for speed
                
                plan = self.planner.plan_next_step(goal, current_state, screenshot_bytes)
                next_action = plan.get("next_action")
                target = plan.get("target")
                tool = plan.get("tool_preference")
                thought = plan.get("thought_process")
                
                if telegram_callback:
                    await telegram_callback(
                        f"🧠 **Gedanke:** {thought}\n"
                        f"⚙️ **Aktion:** `{next_action}` -> `{target}`"
                    )

                if next_action == "ERROR":
                    logger.error("Planner returned an error.")
                    await context.close()
                    return {"success": False, "error": target, "state": current_state}
                    
                if next_action == "FINISH":
                    logger.info(f"[Executor] Goal achieved. Result: {target}")
                    # Send final screenshot
                    await self._send_telegram_photo(telegram_callback, caption="✅ Ziel erreicht")
                    
                    # CRITICAL: We DO NOT close the context here if we want to keep it open for user inspection?
                    # BUT for this specific 'run' function, it must end. 
                    # The browser process dies when the python script ends usually.
                    # Unless we detach it. For now, we close it to save resources, but we SAVED the session to disk.
                    await context.close()
                    return {"success": True, "result": target, "state": current_state}
                
                # ACT
                logger.info(f"[Executor] Executing action: {next_action} via {tool} on {target}")
                action_result = await self._execute_action(page, plan, current_state)
                
                # Auto-Screenshot after action
                await self._send_telegram_photo(telegram_callback, caption=f"Ende Schritt {step_count}: {next_action}")

                # OBSERVE
                current_state["last_action_result"] = action_result
                
                if not action_result.get("success"):
                    consecutive_failures += 1
                    logger.warning(f"[Executor] Action failed ({consecutive_failures}/{self.max_retries}). Retrying... Error: {action_result.get('error')}")
                    if consecutive_failures >= self.max_retries:
                        await context.close()
                        return {"success": False, "error": f"Max retries ({self.max_retries}) reached. Last error: {action_result.get('error')}", "state": current_state}
                else:
                    consecutive_failures = 0
                    
            await context.close()
        return {"success": False, "error": "Safety limit (10 steps) reached", "state": current_state}
        
    async def _execute_action(self, page, plan: Dict[str, Any], current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Executes a single action based on the plan using Playwright or CVBot fallback.
        """
        action = plan.get("next_action")
        target = plan.get("target")
        tool = plan.get("tool_preference")
        
        try:
            if action == "GOTO_URL":
                await page.goto(target, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(3) # Wait for render
                return {"success": True, "details": f"Successfully navigated to {target}"}
                
            elif action == "SEARCH":
                if tool == "DOM_SCRAPE":
                    # Try generic selectors for search bars
                    input_locator = page.locator('input[name="q"], input[type="search"], input[aria-label="Search"], input[title="Search"]').first
                    if await input_locator.count() > 0:
                        try:
                            await input_locator.fill(target, timeout=5000)
                            await input_locator.press("Enter")
                            await page.wait_for_load_state("domcontentloaded")
                            await asyncio.sleep(3)
                            return {"success": True, "details": f"Entered search term: {target}"}
                        except Exception as e:
                            logger.warning(f"DOM SEARCH fill failed: {e}. Falling back to Vision.")
                            tool = "VISION_CLICK" # Dynamic fallback
                    else:
                        tool = "VISION_CLICK"
                
                if tool == "VISION_CLICK":
                    return await self._click_via_vision(target, type_text=True)
                    
            elif action == "CLICK":
                if tool == "DOM_SCRAPE":
                    try:
                        # Improved clicking: Try exact text, then partial, then selector
                        await page.click(f"text={target}", timeout=5000)
                        await page.wait_for_load_state("domcontentloaded")
                        return {"success": True, "details": f"Clicked on element containing '{target}'"}
                    except Exception as e:
                        logger.warning(f"DOM CLICK failed: {e}. Falling back to Vision.")
                        tool = "VISION_CLICK"
                
                if tool == "VISION_CLICK":
                    return await self._click_via_vision(target)
                    
            elif action == "EXTRACT":
                # Always extract text for context
                content = await page.evaluate("document.body.innerText")
                content = content[:2000]
                return {"success": True, "details": f"Extracted text data: {content}"}
                    
            return {"success": False, "error": f"Unknown action: {action}"}
            
        except Exception as e:
            logger.error(f"[Executor] Action threw exception: {e}")
            return {"success": False, "error": str(e)}

    async def _click_via_vision(self, target: str, type_text: bool = False) -> Dict[str, Any]:
        """Helper to use CVBotTool for vision-based interaction."""
        try:
            with mss.mss() as sct:
                monitor = sct.monitors[1] # DISPLAY :99
                sct_img = sct.grab(monitor)
                img_bgra = np.array(sct_img)
                img_bgr = cv2.cvtColor(img_bgra, cv2.COLOR_BGRA2BGR)
                
                # Encode to bytes for Gemini Vision
                _, buffer = cv2.imencode(".png", img_bgr)
                img_bytes = buffer.tobytes()
                
                result = await self.cv_tool.find_element_via_vision(
                    img_bytes, 
                    target, 
                    original_bgra=img_bgra,
                    offset_x=monitor["left"],
                    offset_y=monitor["top"]
                )
                
                if result.get("found"):
                    x, y = result["x"], result["y"]
                    # Move and click via xdotool
                    os.system(f"export DISPLAY=:99 && xdotool mousemove {x} {y} click 1")
                    await asyncio.sleep(1)
                    if type_text:
                        # Clear field first or just type
                        os.system(f"export DISPLAY=:99 && xdotool type --delay 100 '{target}' && xdotool key Return")
                    return {"success": True, "details": f"Vision: Found and clicked {target} at {x},{y}"}
                else:
                    return {"success": False, "error": f"Vision: Could not find {target} on screen"}
        except Exception as e:
            return {"success": False, "error": f"Vision error: {str(e)}"}
