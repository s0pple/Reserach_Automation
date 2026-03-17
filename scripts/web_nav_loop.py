import asyncio
import os
import sys
import json
import base64
from playwright.async_api import async_playwright
from telegram import Bot

# Config
PROFILE_PATH = "/app/browser_sessions/account_cassie"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Get Chat ID
try:
    ALLOWED = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
    CHAT_ID = [id.strip() for id in ALLOWED.split(",") if id.strip()][0]
except IndexError:
    print("❌ Error: No allowed Telegram User IDs found in env.")
    sys.exit(1)

async def send_msg(text):
    if not TOKEN: return
    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print(f"⚠️ Msg Error: {e}")

async def send_screenshot(page, caption=""):
    if not TOKEN: return
    path = "temp/web_nav_screenshot.png"
    try:
        await page.screenshot(path=path)
        bot = Bot(token=TOKEN)
        with open(path, "rb") as f:
            await bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption)
    except Exception as e:
        print(f"⚠️ Screenshot Error: {e}")

async def main():
    # Goal comes from command line arg
    if len(sys.argv) < 2:
        print("Usage: python3 web_nav_loop.py <GOAL>")
        return
        
    goal = sys.argv[1]
    print(f"🚀 Starting Gemini Web Nav Loop for: {goal}")
    await send_msg(f"🚀 **Web Nav Loop gestartet**\nZiel: `{goal}`")

    async with async_playwright() as p:
        # Use existing Xvfb display if available
        headless = False
        args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=headless,
            args=args,
            viewport={"width": 1280, "height": 800}
        )
        
        # We need TWO pages:
        # Page 1: The "Brain" (AI Studio with the plan)
        # Page 2: The "Worker" (Browsing the web)
        
        brain_page = context.pages[0] if context.pages else await context.new_page()
        worker_page = await context.new_page()
        
        try:
            # 1. Init Brain (AI Studio)
            print("🧠 Loading Brain (AI Studio)...")
            await brain_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await brain_page.wait_for_timeout(5000)
            
            # --- Handle Modals/Banners ---
            try:
                # Common buttons in German/English AI Studio
                banners = brain_page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept"), button:has-text("Get started")')
                if await banners.count() > 0:
                    print("🧹 Cleaning up AI Studio Banners...")
                    await banners.first.click()
                    await brain_page.wait_for_timeout(2000)
            except:
                pass

            # 2. Initial Prompt to Brain
            initial_prompt = f"""You are an autonomous web browsing agent. 
Your goal is: "{goal}"

I will provide you with screenshots of the current web page.
You must decide the NEXT ACTION to take to achieve the goal.

Respond ONLY with a valid JSON object:
{{
  "thought": "Reasoning for this step",
  "action": "GOTO" | "CLICK" | "TYPE" | "SCROLL" | "FINISH",
  "param": "The URL, selector/text, or answer"
}}

Example:
{{ "thought": "I need to search Google", "action": "GOTO", "param": "https://www.google.com" }}
{{ "thought": "I see the search bar", "action": "TYPE", "param": "Bitcoin Price" }}

Let's start! Waiting for first screenshot...
"""
            # Type prompt into brain
            await brain_page.locator("textarea").fill(initial_prompt)
            await brain_page.keyboard.press("Control+Enter")
            await brain_page.wait_for_timeout(5000) # Wait for Brain to ack (we ignore first response mostly)
            
            # 3. The Loop
            step = 0
            max_steps = 10
            
            while step < max_steps:
                step += 1
                print(f"🔄 Step {step}/{max_steps}")
                
                # A. Snapshot Worker
                screenshot_path = f"temp/step_{step}.png"
                await worker_page.screenshot(path=screenshot_path)
                
                # B. Upload to Brain
                try:
                    # 1. Click "+" button (Aria label or text)
                    plus_button = brain_page.locator('button[aria-label*="Insert"], button:has-text("add_circle"), .add-content-button')
                    if await plus_button.count() > 0:
                        await plus_button.first.click(force=True)
                        await brain_page.wait_for_timeout(1000)
                        
                        # 2. Click "Upload files" menu item
                        upload_item = brain_page.locator('.mat-mdc-menu-item:has-text("Upload"), [role="menuitem"]:has-text("Upload")')
                        if await upload_item.count() > 0:
                            await upload_item.first.click()
                            await brain_page.wait_for_timeout(1000)
                    
                    # 3. Finally, upload the file
                    file_input = brain_page.locator('input[type="file"]')
                    if await file_input.count() > 0:
                        await file_input.first.set_input_files(screenshot_path)
                    else:
                        print("⚠️ Could not find file input for image upload!")
                        await send_msg("⚠️ **Vision Error:** Upload-Feld in AI Studio nicht gefunden.")
                        break
                        
                    await brain_page.wait_for_timeout(3000) # Wait for upload preview
                    
                    # C. Ask for Next Step
                    prompt = f"Step {step}. Current URL: {worker_page.url}. What next? Respond only with JSON."
                    # Find the prompt textarea (it might change after image upload)
                    textarea = brain_page.locator('textarea, div[contenteditable="true"]').last
                    await textarea.fill(prompt)
                    await brain_page.keyboard.press("Control+Enter")
                    
                    # D. Wait for Response (Stream)
                    await brain_page.wait_for_timeout(8000) # Wait for generation
                    
                    # E. Extract Response (Last message)
                    content = await brain_page.evaluate("document.body.innerText")
                    
                    # Robust JSON Extraction Strategy
                    import re
                    # Look for JSON blocks that specifically contain "action" and "thought"
                    # We use a non-greedy dot match, but we might need to handle newlines.
                    # Strategy: Find all {...} blocks and parse them to see if they are valid plans.
                    
                    # 1. Try to find all JSON-like strings
                    potential_jsons = re.findall(r'\{[^{}]*\}', content) # Simple flat JSON
                    # If nested, we need recursive or just allow braces.
                    # Let's try a regex that matches { ... "action": ... }
                    
                    # Fallback: Just look for the last occurrence of "{"action"" or "{"thought""
                    # and try to parse from there to the end.
                    
                    valid_plan = None
                    
                    # Split content by "}" to get potential ends
                    fragments = content.split('}')
                    
                    # Iterate backwards to find the latest response
                    for i in range(len(fragments)-1, -1, -1):
                        # Reconstruct a potential JSON string from the end
                        candidate = "}".join(fragments[i:]) + "}"
                        # Find the last "{"
                        start_idx = candidate.rfind('{')
                        if start_idx == -1: continue
                        
                        json_str = candidate[start_idx:]
                        
                        # Cleanup (sometimes newlines or markdown wraps it)
                        json_str = json_str.strip()
                        if json_str.startswith("```json"): json_str = json_str[7:]
                        if json_str.endswith("```"): json_str = json_str[:-3]
                        
                        try:
                            plan = json.loads(json_str)
                            if "action" in plan and "thought" in plan:
                                valid_plan = plan
                                break
                        except:
                            continue
                            
                    if not valid_plan:
                        print("⚠️ No valid Plan JSON found in response!")
                        # Debug: Print last part of content
                        debug_text = content[-500:].replace('\n', ' ')
                        print(f"DEBUG CONTENT: {debug_text}")
                        await send_msg(f"⚠️ **Brain Error:** Kein valider Plan gefunden.\nContext: `{debug_text}`")
                        continue
                        
                    thought = valid_plan.get("thought")
                    action = valid_plan.get("action")
                    param = valid_plan.get("param")
                    
                    print(f"🧠 Brain says: {thought} -> {action} {param}")
                    await send_msg(f"🧠 **Gedanke:** {thought}\n⚡ **Aktion:** `{action}` {param}")
                    
                    # F. Execute Action on Worker
                    if action == "GOTO":
                        await worker_page.goto(param)
                    elif action == "CLICK":
                        await worker_page.click(f"text={param}") # Fuzzy text click
                    elif action == "TYPE":
                        await worker_page.keyboard.type(param)
                        await worker_page.keyboard.press("Enter")
                    elif action == "FINISH":
                        print("✅ Goal Reached!")
                        await send_msg(f"✅ **Ziel Erreicht:** {param}")
                        break
                    
                    await worker_page.wait_for_timeout(3000)
                    await send_screenshot(worker_page, f"Step {step}: After {action}")

                except Exception as e:
                    print(f"💥 Loop Error: {e}")
                    await send_msg(f"💥 Fehler im Loop: {e}")
                    break

        except Exception as e:
            print(f"💥 Setup Error: {e}")
            await send_msg(f"💥 Setup Fehler: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())
