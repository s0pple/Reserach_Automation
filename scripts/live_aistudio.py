import asyncio
import os
import sys
import json
from playwright.async_api import async_playwright
from telegram import Bot
from src.modules.browser.ui_mapper import get_ui_map, find_in_map

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
        if len(text) > 4000:
            for i in range(0, len(text), 4000):
                await bot.send_message(chat_id=CHAT_ID, text=text[i:i+4000])
        else:
            await bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print(f"⚠️ Msg Error: {e}")

async def send_screenshot(page, caption=""):
    if not TOKEN: return
    path = "temp/live_monitor.png"
    try:
        await page.screenshot(path=path)
        bot = Bot(token=TOKEN)
        with open(path, "rb") as f:
            await bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption)
    except Exception as e:
        print(f"⚠️ Screenshot Error: {e}")

async def main():
    print("🚀 Starting Grounded AI Studio Bridge...")
    await send_msg("🚀 **AI Studio Bridge Online (Grounded)**\nBefehle:\n- `new` (Reset)\n- `prompt <text>` (Chat)\n- `find <element>` (Grounded Search & Click)")

    async with async_playwright() as p:
        headless = False 
        args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=headless,
            args=args,
            viewport={"width": 1280, "height": 800}
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            # Initial Load
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Dismiss Banners
            try:
                banners = page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
                if await banners.count() > 0:
                    await banners.first.click(force=True)
            except: pass

            await send_screenshot(page, "✅ Ready.")

            while True:
                print("\n👇 WAITING FOR INPUT...")
                command_line = await asyncio.to_thread(input, "")
                command_line = command_line.strip()
                if not command_line: continue
                
                cmd_parts = command_line.split(" ", 1)
                action = cmd_parts[0].lower()
                payload = cmd_parts[1] if len(cmd_parts) > 1 else ""
                
                if action == "exit": break
                
                elif action in ["new", "neu", "reset"]:
                    await page.goto("https://aistudio.google.com/app/prompts/new_chat")
                    await page.wait_for_timeout(3000)
                    await send_screenshot(page, "🔄 Reset.")
                    
                elif action in ["type", "prompt", "reflect", "find"]:
                    is_grounded = (action == "find")
                    is_reflection = (action in ["reflect", "find"])
                    
                    try:
                        path = "temp/current_screen.png"
                        await page.screenshot(path=path)
                        
                        ui_map = []
                        if is_grounded:
                            await send_msg("🔍 Erstelle Ground-Truth Map...")
                            with open(path, "rb") as f:
                                ui_map = await get_ui_map(f.read())
                            prompt_payload = f"Liste der UI-Elemente: {json.dumps(ui_map)}. Ziel: '{payload}'. Welches exakte Element-Label muss ich klicken? Antworte NUR mit dem Label."
                        else:
                            prompt_payload = payload

                        # Upload for reflection
                        if is_reflection:
                            plus = page.locator('button[aria-label*="Insert"], button:has-text("add_circle")')
                            if await plus.count() > 0:
                                await plus.first.click()
                                await page.wait_for_timeout(500)
                                await page.locator('role=menuitem:has-text("Upload")').click()
                                await page.locator('input[type="file"]').set_input_files(path)
                                await page.wait_for_timeout(2000)
                            prompt_prefix = "Basierend auf dem Bild: "
                        else:
                            prompt_prefix = ""

                        # Send Prompt
                        textarea = page.locator('textarea, div[contenteditable="true"]').last
                        await textarea.fill(f"{prompt_prefix}{prompt_payload}")
                        await page.keyboard.press("Control+Enter")
                        await send_msg("⏳ Gemini plant...")

                        # Wait & Scrape
                        await asyncio.sleep(5)
                        stop_btn = page.locator('button:has-text("Stop")')
                        for _ in range(20):
                            if await stop_btn.count() == 0: break
                            await asyncio.sleep(1)
                        
                        response_locator = page.locator('div.model-response-text, div.markdown-renderer').last
                        response_text = await response_locator.inner_text() if await response_locator.count() > 0 else "Extraktion fehlgeschlagen."

                        if is_grounded:
                            target_label = response_text.strip().strip('"')
                            match = find_in_map(ui_map, target_label)
                            if match:
                                await send_msg(f"🎯 Klicke '{match['text']}' @ {match['x']},{match['y']}")
                                await page.mouse.click(match['x'], match['y'])
                                await page.wait_for_timeout(2000)
                                await send_screenshot(page, "✅ Aktion ausgeführt")
                            else:
                                await send_msg(f"❌ '{target_label}' nicht in Map gefunden.")
                        else:
                            await send_msg(f"📝 Antwort:\n{response_text[:3000]}")
                            await send_screenshot(page, "📸 View")

                    except Exception as e:
                        await send_msg(f"💥 Fehler: {e}")
                        
                elif action == "screenshot":
                     await send_screenshot(page, "📸 Screen")

        except Exception as e:
            await send_msg(f"💥 Fatal: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())
