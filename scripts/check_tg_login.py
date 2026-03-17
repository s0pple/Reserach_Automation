import asyncio
import os
import sys
from playwright.async_api import async_playwright

PROFILE_PATH = "/app/browser_sessions/telegram_tester"

async def check_telegram_login():
    print(f"🔍 Checking Telegram Login Status in: {PROFILE_PATH}")
    async with async_playwright() as p:
        headless = True # Start headless to avoid Xvfb mess if just checking
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
            await page.goto("https://web.telegram.org/a/", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Check for common login elements (e.g. login form vs chat list)
            if "login" in page.url or await page.locator("button:has-text('LOG IN')").count() > 0:
                print("❌ NOT LOGGED IN to Telegram Web.")
                await page.screenshot(path="temp/tg_login_fail.png")
            else:
                print("✅ LOGGED IN to Telegram Web!")
                await page.screenshot(path="temp/tg_login_success.png")
                # List visible chat names?
                chats = await page.locator(".chat-info .title").all_inner_texts()
                print(f"Visible Chats: {chats[:10]}")
                
        except Exception as e:
            print(f"💥 Error checking login: {e}")
            await page.screenshot(path="temp/tg_login_error.png")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(check_telegram_login())
