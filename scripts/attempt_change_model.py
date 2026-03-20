import asyncio
from playwright.async_api import async_playwright

PROFILE_PATH = "browser_sessions/account_cassie"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

async def change_model():
    print("[FIX] 🟢 Changing Model...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto(AI_STUDIO_URL)
        
        # 1. Open Model Selector
        print("[FIX] 🔍 Clicking model selector...")
        # The selector from the dump seemed to be 'ms-model-selector button.model-selector-card'
        selector_btn = page.locator("ms-model-selector button")
        await selector_btn.click()
        await asyncio.sleep(1)
        
        # 2. Select Gemini 1.5 Flash (or anything else)
        # Assuming a list of buttons in a dropdown or dialog
        # Let's dump the options first to be safe
        options = page.locator("button.mat-mdc-menu-item")
        count = await options.count()
        print(f"[FIX] Found {count} model options.")
        
        target_model = "Gemini 1.5 Flash" # Safe bet
        found = False
        
        for i in range(count):
            txt = await options.nth(i).inner_text()
            print(f"   - Option {i}: {txt}")
            if target_model in txt:
                print(f"[FIX] ✅ Selecting: {txt}")
                await options.nth(i).click()
                found = True
                break
        
        if not found:
            print("[FIX] ⚠️ Target model not found! Selecting first available option.")
            if count > 0:
                await options.first.click()
        
        await asyncio.sleep(2)
        
        # 3. Retry Prompt
        print("[FIX] 🔄 Retrying prompt with new model...")
        textarea = page.locator("textarea")
        await textarea.fill("Hello Gemini 1.5")
        await page.keyboard.press("Control+Enter")
        
        await asyncio.sleep(5)
        
        # Check success
        chunks = page.locator("ms-text-chunk")
        if await chunks.count() > 0:
            print(f"[FIX] ✅ SUCCESS! Response: {await chunks.last.inner_text()}")
        else:
            print("[FIX] ❌ Still failing.")
            await page.screenshot(path="debug_fix_model.png")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(change_model())
