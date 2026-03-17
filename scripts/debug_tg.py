import asyncio
import os
import sys
from playwright.async_api import async_playwright

PROFILE_PATH = "/app/browser_sessions/telegram_tester"

async def debug_tg():
    print(f"🌍 Loading Telegram Web for Debug...")
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
            await page.goto("https://web.telegram.org/a/", timeout=60000)
            await page.wait_for_timeout(10000)
            await page.screenshot(path="temp/tg_debug_main.png")
            print("📸 Main Screen saved.")
            
            # List all text on screen to find chat names
            text = await page.evaluate("document.body.innerText")
            print(f"--- SCREEN TEXT ---\n{text[:1000]}\n---")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(debug_tg())
