import asyncio
from playwright.async_api import async_playwright, expect

PROFILE_PATH = "browser_sessions/account_cassie"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

async def fix_and_test():
    print("[FIX] 🟢 Starting Fix Attempt...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(AI_STUDIO_URL)
        
        # 1. Disable Grounding
        print("[FIX] 🔍 Looking for 'Remove Grounding' button...")
        remove_btn = page.locator("button[aria-label='Remove Grounding with Google Search']")
        
        try:
            if await remove_btn.count() > 0 and await remove_btn.is_visible():
                await remove_btn.click()
                print("[FIX] 🛠️ Clicked 'Remove Grounding'.")
                await asyncio.sleep(1)
            else:
                print("[FIX] ⚠️ 'Remove Grounding' button not found or not visible.")
        except Exception as e:
            print(f"[FIX] ⚠️ Error removing grounding: {e}")

        # 2. Try Prompting
        print("[FIX] 🔄 Retrying prompt...")
        textarea = page.locator("textarea")
        await textarea.wait_for(state="visible", timeout=10000)
        await textarea.fill("Hello")
        await page.keyboard.press("Control+Enter")
        
        # 3. Wait and Check
        print("[FIX] ⏳ Waiting for result...")
        await asyncio.sleep(5)
        
        # Check for error again
        errors = page.locator("ms-callout.error-callout")
        if await errors.count() > 0:
            print("[FIX] ❌ Error still present!")
            print(await errors.all_inner_texts())
        else:
            chunks = page.locator("ms-text-chunk")
            count = await chunks.count()
            if count > 0:
                print(f"[FIX] ✅ Success! Found {count} chunks.")
                print(await chunks.last.inner_text())
            else:
                print("[FIX] ❓ No error, but no chunks yet.")
                
        await page.screenshot(path="debug_fix_attempt.png")
        await context.close()

if __name__ == "__main__":
    asyncio.run(fix_and_test())
