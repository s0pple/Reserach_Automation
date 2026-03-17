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

# Config
PROFILE_PATH = "/app/browser_sessions/account_cassie"
EMAIL = "cassie.blackw0d@gmail.com"
# PASSWORD provided in context
PASSWORD = "Gemini1212!"
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# Get Chat ID safely
try:
    ALLOWED = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
    CHAT_ID = [id.strip() for id in ALLOWED.split(",") if id.strip()][0]
except IndexError:
    print("❌ Error: No allowed Telegram User IDs found in env.")
    sys.exit(1)

async def send_telegram_msg(text):
    if not TOKEN: return
    try:
        bot = Bot(token=TOKEN)
        await bot.send_message(chat_id=CHAT_ID, text=text)
    except Exception as e:
        print(f"⚠️ Telegram Msg Error: {e}")

async def send_screenshot(page, caption):
    if not TOKEN: return
    path = "temp/setup_screenshot.png"
    try:
        await page.screenshot(path=path)
        bot = Bot(token=TOKEN)
        with open(path, "rb") as f:
            await bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption)
    except Exception as e:
        print(f"⚠️ Screenshot Error: {e}")

async def main():
    print("🚀 Starting Setup for Account: Cassie")
    await send_telegram_msg("🚀 Starting Google Account Setup script...")

    async with async_playwright() as p:
        # Use existing Xvfb display if available, else headless
        headless = False
        args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        
        if not os.getenv("DISPLAY"):
            os.environ["DISPLAY"] = ":99" 
        
        print(f"📂 Profile: {PROFILE_PATH}")
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=headless,
            args=args,
            viewport={"width": 1280, "height": 800}
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            print("🌍 Navigating to Google AI Studio...")
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # 1. Check Login State
            if "accounts.google.com" in page.url:
                print("🔒 Login Page detected.")
                await send_screenshot(page, "🔒 Login Required")
                
                # 2. Email
                email_input = page.locator('input[type="email"]')
                if await email_input.count() > 0 and await email_input.is_visible():
                    print(f"⌨️ Entering email: {EMAIL}")
                    await email_input.fill(EMAIL)
                    await page.wait_for_timeout(1000)
                    await page.keyboard.press("Enter")
                    # Wait for password field
                    await page.wait_for_timeout(3000)
                
                # 3. Password
                pass_input = page.locator('input[type="password"]')
                if await pass_input.count() > 0 and await pass_input.is_visible():
                    print("⌨️ Entering password...")
                    await pass_input.fill(PASSWORD)
                    await page.wait_for_timeout(1000)
                    await page.keyboard.press("Enter")
                    await page.wait_for_timeout(5000)
                    await send_screenshot(page, "🔑 Password Submitted")
                
                # 4. Check for 2FA / Challenges
                if "challenge" in page.url or "signin" in page.url:
                    print("⚠️ Additional verification likely needed.")
                    await send_screenshot(page, "⚠️ Action Required: Check Telegram!")
                    
                    # Interactive Loop
                    while True:
                        print("\n👇 INTERACTIVE MODE 👇")
                        print("What should I do? Options:")
                        print(" - Type a code (e.g. 123456)")
                        print(" - Type 'y' if you approved on phone")
                        print(" - Type 'retry' to screenshot again")
                        print(" - Type 'exit' to stop")
                        
                        user_input = input("Decision > ").strip()
                        
                        if user_input.lower() == 'exit':
                            break
                        elif user_input.lower() == 'retry':
                            await send_screenshot(page, "🔄 Refresh Screenshot")
                            continue
                        elif user_input.lower() == 'y':
                            print("⏳ Waiting for navigation...")
                            await page.wait_for_timeout(5000)
                            await send_screenshot(page, "✅ Post-Approval Check")
                            if "aistudio" in page.url:
                                break
                        else:
                            # Assume it's a code or text to type
                            print(f"⌨️ Typing '{user_input}'...")
                            # Try to find a visible input
                            inputs = page.locator('input:visible')
                            count = await inputs.count()
                            if count > 0:
                                await inputs.first.fill(user_input)
                                await page.keyboard.press("Enter")
                                await page.wait_for_timeout(3000)
                                await send_screenshot(page, "📨 Code Submitted")
                            else:
                                print("❌ No input field found to type into!")
                
            else:
                print("✅ Already logged in (or redirected successfully).")
            
            # Final Check
            await page.wait_for_timeout(3000)
            if "aistudio" in page.url:
                print("🎉 SUCCESS: We are in AI Studio!")
                await send_screenshot(page, "🎉 AI Studio Ready!")
            else:
                print(f"❓ Ended at: {page.url}")
                await send_screenshot(page, "❓ Final Status")

        except Exception as e:
            print(f"💥 Error: {e}")
            await send_telegram_msg(f"💥 Error in script: {e}")
        finally:
            await context.close()
            print("🚪 Browser closed.")

if __name__ == "__main__":
    asyncio.run(main())
