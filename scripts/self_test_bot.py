import asyncio
import os
import sys
from playwright.async_api import async_playwright

PROFILE_PATH = "/app/browser_sessions/telegram_tester"
BOT_USERNAME = "@olivers_orchestrator_bot"
MESSAGE = "Check den Bitcoin Preis auf CoinMarketCap"

async def self_test():
    print(f"🚀 Starting Self-Test: Acting as User via Telegram Web...")
    async with async_playwright() as p:
        headless = False # We want to see it in Xvfb
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
            # 1. Open Telegram Web
            print("🌍 Loading Telegram Web...")
            await page.goto(f"https://web.telegram.org/a/#?q={BOT_USERNAME}", timeout=60000)
            await page.wait_for_timeout(8000)
            
            # Click the bot chat result
            # Selector for chat search results:
            print(f"🔍 Searching for {BOT_USERNAME}...")
            # We can also use the direct URL if we have the peer ID, but search is safer.
            await page.click(f"text={BOT_USERNAME}")
            await page.wait_for_timeout(3000)
            
            # 2. Send Message
            print(f"⌨️  Sending: {MESSAGE}")
            # Selector for the message input box
            input_selector = "#editable-message-text" # Common for Telegram Web 'A'
            await page.click(input_selector)
            await page.keyboard.type(MESSAGE)
            await page.keyboard.press("Enter")
            
            # 3. Monitor Results (Take screenshots every few seconds)
            print("⏳ Monitoring bot's response for 60 seconds...")
            for i in range(12):
                await page.wait_for_timeout(5000)
                path = f"temp/self_test_step_{i}.png"
                await page.screenshot(path=path)
                print(f"📸 Screenshot {i+1}/12 saved to {path}")
                
        except Exception as e:
            print(f"💥 Self-Test Error: {e}")
            await page.screenshot(path="temp/self_test_error.png")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(self_test())
