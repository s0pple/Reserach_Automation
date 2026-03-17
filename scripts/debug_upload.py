import asyncio
import os
import sys
from playwright.async_api import async_playwright

PROFILE_PATH = "/app/browser_sessions/account_cassie"

async def debug_upload():
    print(f"🌍 Detailed AI Studio Upload Debug (V2)...")
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
            
            # 1. Dismiss banners (Forcefully)
            try:
                banners = page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
                if await banners.count() > 0:
                    print("🧹 Banner found, clicking first (Force).")
                    await banners.first.click(force=True)
                    await page.wait_for_timeout(2000)
            except:
                pass

            # 2. List all buttons and their aria-labels
            print("🔍 All Buttons on page:")
            buttons = await page.locator('button').all()
            for btn in buttons:
                txt = await btn.inner_text()
                aria = await btn.get_attribute("aria-label") or ""
                cls = await btn.get_attribute("class") or ""
                print(f"   - Txt: '{txt.strip()}', Aria: '{aria}', Class: '{cls}'")

            # 3. Check for Prompt area
            prompt_area = page.locator('textarea, div[contenteditable="true"]').last
            if await prompt_area.count() > 0:
                print(f"✅ Found Prompt Area. Visibility: {await prompt_area.is_visible()}")
                # Click it to ensure focus
                await prompt_area.click()
                await page.wait_for_timeout(1000)
                
            # 4. Search for the "+" button (Add content)
            # In some versions it's 'ms-add-content-button' or aria-label 'Add content'
            plus = page.locator('button[aria-label*="content"], button[aria-label*="Add"], .add-content-button')
            if await plus.count() > 0:
                print(f"✅ Found {await plus.count()} potential '+' buttons.")
                # Try clicking the first one
                try:
                    await plus.first.click()
                    print("   -> Clicked '+' button.")
                    await page.wait_for_timeout(2000)
                except Exception as e:
                    print(f"   -> Failed to click '+': {e}")

            # 5. Final check for file inputs
            inputs = await page.locator('input[type="file"]').all()
            print(f"✅ Found {len(inputs)} file inputs.")
            for i, inp in enumerate(inputs):
                aria = await inp.get_attribute("aria-label") or ""
                print(f"   [Input {i}] Aria: '{aria}'")
                
            await page.screenshot(path="temp/upload_debug_final_v2.png")
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(debug_upload())
