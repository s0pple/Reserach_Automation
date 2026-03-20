import os
import asyncio
from playwright.async_api import async_playwright

async def verify():
    async with async_playwright() as p:
        print("Launching Browser with 'account_cassie'...")
        # Try to use the existing session
        context = await p.chromium.launch_persistent_context(
            user_data_dir="browser_sessions/account_cassie",
            headless=True, # Headless for verification
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        print("Navigating to AI Studio...")
        await page.goto("https://aistudio.google.com/app/prompts/new_chat")
        
        print("Waiting for network idle...")
        await page.wait_for_load_state("networkidle")
        
        # Take screenshot
        screenshot_path = "verify_session_cassie.png"
        await page.screenshot(path=screenshot_path)
        print(f"Screenshot saved to {screenshot_path}")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(verify())
