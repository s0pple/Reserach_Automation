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
        # Handle splitting if needed
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
    print("🚀 Starting GROUNDED AUTO-LOOP Controller...")
    await send_msg("🚀 **Grounded Explorer Online**\nModus: Auto-Loop Only.\nBefehle: `auto <ziel>`, `stop`, `new`")

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
            # 1. Initial Load
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Dismiss Banners
            try:
                banners = page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
                if await banners.count() > 0:
                    await banners.first.click(force=True)
            except: pass

            await send_screenshot(page, "✅ AI Studio geladen.")

            while True:
                print("\n👇 WAITING FOR COMMAND (auto <goal>)...")
                command_line = await asyncio.to_thread(input, "")
                command_line = command_line.strip()
                if not command_line: continue
                
                cmd_parts = command_line.split(" ", 1)
                action = cmd_parts[0].lower()
                payload = cmd_parts[1] if len(cmd_parts) > 1 else ""
                
                if action == "stop":
                    await send_msg("🛑 Loop gestoppt.")
                    continue
                
                elif action in ["new", "reset"]:
                    await page.goto("https://aistudio.google.com/app/prompts/new_chat")
                    await page.wait_for_timeout(3000)
                    await send_screenshot(page, "🔄 Reset.")
                    continue

                elif action == "auto":
                    goal = payload
                    await send_msg(f"🕵️ **Starte Grounded Explorer**\nZiel: `{goal}`")
                    
                    history = []
                    for step in range(1, 11): # Max 10 Steps
                        print(f"--- STEP {step} ---")
                        
                        # A. Snapshot & OCR Map
                        path = f"temp/step_{step}.png"
                        await page.screenshot(path=path)
                        
                        await send_msg(f"🔄 **Schritt {step}:** Scanne Realität...")
                        with open(path, "rb") as f:
                            ui_map = await get_ui_map(f.read())
                        
                        if not ui_map:
                            await send_msg("❌ Konnte UI Map nicht erstellen. Breche ab.")
                            break
                            
                        # B. Formulate Planner Prompt (AI Studio as Brain)
                        # We use the current UI map to ground the LLM
                        map_json = json.dumps([{"text": el['text'], "type": el.get('type', 'button')} for el in ui_map[:30]])
                        
                        planner_prompt = f"""
                        DU BIST EIN UI-AGENT.
                        ZIEL: {goal}
                        REALITÄT (Sichtbare Elemente): {map_json}
                        HISTORIE: {history[-3:]}
                        
                        GIB MIR NUR DEN EXAKTEN TEXT DES NÄCHSTEN BUTTONS/ELEMENTS ZUM KLICKEN.
                        WENN FERTIG, ANTWORTE: 'FINISH'.
                        ANTWORTE NUR MIT DEM LABEL.
                        """
                        
                        # C. Upload & Ask AI Studio
                        textarea = page.locator('textarea, div[contenteditable="true"]').last
                        await textarea.fill(planner_prompt)
                        await page.keyboard.press("Control+Enter")
                        
                        await send_msg(f"🧠 **Thinking...** (Schritt {step})")
                        
                        # Wait for Answer
                        await asyncio.sleep(5)
                        stop_btn = page.locator('button:has-text("Stop")')
                        for _ in range(15):
                            if await stop_btn.count() == 0: break
                            await asyncio.sleep(1)
                        
                        # Scrape Answer
                        response_locator = page.locator('div.model-response-text, div.markdown-renderer').last
                        decision = await response_locator.inner_text() if await response_locator.count() > 0 else ""
                        decision = decision.strip().strip('"')
                        
                        if "FINISH" in decision.upper():
                            await send_msg(f"✅ **Mission beendet:** {decision}")
                            break
                            
                        # D. Reality Matching & Execution
                        match = find_in_map(ui_map, decision)
                        if match:
                            await send_msg(f"🎯 **Aktion:** Klicke '{match['text']}'")
                            await page.mouse.click(match['x'], match['y'])
                            history.append(f"Clicked {match['text']}")
                            await page.wait_for_timeout(3000)
                            await send_screenshot(page, f"✅ Schritt {step} ausgeführt.")
                        else:
                            await send_msg(f"⚠️ **Halluzination erkannt:** '{decision}' nicht in Map gefunden. Versuche Fallback...")
                            # Fallback: Klicke auf Enter oder Scroll?
                            await page.keyboard.press("Escape")
                            history.append(f"Failed to find {decision}")
                            
                        # Check for Loop (Anti-Repeat)
                        if len(history) >= 3 and len(set(history[-3:])) == 1:
                            await send_msg("🚨 **Loop erkannt!** Breche ab.")
                            break
                    
                    await send_msg(f"🏁 **Exploration beendet** (Schritte: {step})")

                else:
                    await send_msg(f"❓ Unbekannt: {action}. Nutze 'auto <ziel>'")

        except Exception as e:
            await send_msg(f"💥 Fataler Fehler im Script: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())
