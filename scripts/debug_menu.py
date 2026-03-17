import asyncio
import os
import sys
from playwright.async_api import async_playwright

PROFILE_PATH = "/app/browser_sessions/account_cassie"

async def debug_menu():
    print(f"🌍 AI Studio Menu Debug...")
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
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await page.wait_for_timeout(7000)
            
            # Click the "add_circle" button
            plus = page.locator('button[aria-label*="Insert"], button:has-text("add_circle")')
            if await plus.count() > 0:
                print("✅ Found '+' button. Clicking...")
                await plus.first.click()
                await page.wait_for_timeout(2000)
                
                # List menu items
                print("🔍 Menu items:")
                menu_items = await page.locator('.mat-mdc-menu-item, [role="menuitem"]').all()
                for item in menu_items:
                    txt = await item.inner_text()
                    print(f"   - Item: '{txt.strip()}'")
                
                # Check for file input now
                inputs = await page.locator('input[type="file"]').all()
                print(f"✅ Found {len(inputs)} file inputs after click.")
                
            await page.screenshot(path="temp/menu_debug.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(debug_menu())
