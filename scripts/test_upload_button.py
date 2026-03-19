import asyncio
import os
from playwright.async_api import async_playwright

PROFILE_PATH = "/app/browser_sessions/account_cassie"

async def test_upload_button():
    async with async_playwright() as p:
        args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=True,
            args=args,
            viewport={"width": 1280, "height": 800}
        )
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await page.wait_for_timeout(5000)
        
        # Click the insert button
        btn = page.locator('button[aria-label="Insert images, videos, audio, or files"]')
        if await btn.count() > 0:
            await btn.click()
            await page.wait_for_timeout(1000)
            
            menu_items = await page.locator('[role="menuitem"]').all()
            print(f"Found {len(menu_items)} menu items.")
            for i, item in enumerate(menu_items):
                text = await item.inner_text()
                print(f"Menu item {i}: {text.strip()}")
                
            inputs = await page.locator('input[type="file"]').all()
            print(f"Found {len(inputs)} file inputs after click.")
        else:
            print("Insert button not found.")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_upload_button())