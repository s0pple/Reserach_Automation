import asyncio
import os
import sys
from playwright.async_api import async_playwright
from telegram import Bot

# Load env if needed
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Config - Reuse the same profile we just set up!
PROFILE_PATH = "/app/browser_sessions/account_cassie"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Get Chat ID safely
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
    path = "temp/live_screenshot.png"
    try:
        await page.screenshot(path=path)
        bot = Bot(token=TOKEN)
        with open(path, "rb") as f:
            await bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption)
    except Exception as e:
        print(f"⚠️ Screenshot Error: {e}")

async def main():
    print("🚀 Starting LIVE AI Studio Controller")
    await send_msg("🚀 Live-Controller gestartet! Warte auf Befehle...\n(new, model <name>, type <text>, send, exit)")

    async with async_playwright() as p:
        headless = False # We need to see it (or Xvfb sees it)
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
            print("🌍 Navigating to AI Studio...")
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await page.wait_for_timeout(3000)
            await send_screenshot(page, "✅ Ready in AI Studio")

            while True:
                # 1. Wait for command from Stdin (piped from Telegram)
                print("\n👇 WAITING FOR COMMAND 👇")
                print("Type 'new', 'model <name>', 'type <text>', 'send', or 'exit'")
                
                # This input() blocks until the user sends a message via /cli input
                command = await asyncio.to_thread(input, "Command > ")
                command = command.strip()
                
                if not command: continue
                
                cmd_lower = command.lower()
                
                if cmd_lower == "exit":
                    await send_msg("👋 Closing Session.")
                    break
                
                elif cmd_lower.startswith("new") or cmd_lower.startswith("neu"):
                    print("🆕 Creating New Chat...")
                    # Try to find 'Create new' or similar button
                    # The URL often resets state, or look for specific button
                    await page.goto("https://aistudio.google.com/app/prompts/new_chat")
                    await page.wait_for_timeout(2000)
                    await send_screenshot(page, "🆕 New Chat Created")
                    
                elif cmd_lower.startswith("model"):
                    model_name = command[5:].strip() # "model gemini 1.5" -> "gemini 1.5"
                    print(f"🤖 Switching Model to: {model_name}")
                    
                    # Open dropdown (this selector is a guess, needs adjustment based on actual DOM)
                    # We look for something that looks like a model selector.
                    # Usually has aria-label="Select model" or class containing "model-selector"
                    # For now, we try a robust text click approach if possible, or generic
                    
                    # 1. Click the dropdown trigger
                    try:
                        # Attempt to find the model dropdown by common attributes
                        await page.click("button[aria-haspopup='listbox']", timeout=2000) 
                        await page.wait_for_timeout(500)
                        
                        # 2. Type model name to filter (if supported) or click text
                        if model_name:
                             # Try clicking text directly in the dropdown
                             await page.click(f"text={model_name}", timeout=2000)
                    except Exception as e:
                        print(f"⚠️ Model switch failed (trying fallback): {e}")
                        # Fallback: Just print we tried
                        await send_msg(f"⚠️ Konnte Modell-Selector nicht finden. DOM hat sich evtl. geändert.\nFehler: {e}")

                    await page.wait_for_timeout(1000)
                    await send_screenshot(page, f"🤖 Model Attempt: {model_name}")

                elif cmd_lower.startswith("type") or cmd_lower.startswith("prompt"):
                    text_to_type = command.split(" ", 1)[1] if " " in command else ""
                    print(f"⌨️ Typing: {text_to_type}")
                    
                    # Focus the main prompt area. Usually a textarea or contenteditable div.
                    # Common selector for AI Studio prompt box:
                    selector = "textarea" 
                    # If multiple, usually the last one or largest is the prompt
                    
                    try:
                        await page.click(selector)
                        await page.keyboard.type(text_to_type)
                        await send_screenshot(page, "⌨️ Typed Text")
                    except Exception as e:
                        await send_msg(f"⚠️ Error typing: {e}")

                elif cmd_lower == "send" or cmd_lower == "run":
                    print("🚀 Sending Prompt...")
                    # Ctrl+Enter is the standard shortcut
                    await page.keyboard.press("Control+Enter")
                    await page.wait_for_timeout(5000) # Wait for response
                    await send_screenshot(page, "🚀 Response Generated?")
                
                else:
                    # Treat unknown commands as just typing? Or error?
                    print(f"❓ Unknown command: {command}")
                    await send_msg(f"❓ Unbekannter Befehl: '{command}'. Nutze: new, model, type, send, exit.")

        except Exception as e:
            await send_msg(f"💥 Critical Error: {e}")
            print(f"Error: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(main())
