import asyncio
import os
import sys
from playwright.async_api import async_playwright

PROFILE_PATH = "/app/browser_sessions/account_cassie"

async def debug_ai_studio():
    print(f"🌍 Loading AI Studio for Debug (Image Upload)...")
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
            await page.wait_for_timeout(5000)
            await page.screenshot(path="temp/ai_studio_upload_debug.png")
            
            # Find all inputs
            inputs = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('input')).map(i => ({
                    type: i.type,
                    id: i.id,
                    className: i.className,
                    ariaLabel: i.ariaLabel
                }));
            }""")
            print(f"Inputs: {inputs}")
            
            # Look for buttons that might trigger upload
            buttons = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('button')).map(b => ({
                    text: b.innerText,
                    ariaLabel: b.ariaLabel
                }));
            }""")
            print(f"Buttons: {buttons[:20]}") # Only first 20
            
        except Exception as e:
            print(f"Error: {e}")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(debug_ai_studio())
