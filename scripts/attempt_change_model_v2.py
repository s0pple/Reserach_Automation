import asyncio
from playwright.async_api import async_playwright

PROFILE_PATH = "browser_sessions/account_cassie"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

async def change_model():
    print("[FIX] 🟢 Changing Model V2...")
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
        selector_btn = page.locator("button.model-selector-card")
        await selector_btn.wait_for(state="visible", timeout=10000)
        await selector_btn.click()
        print("[FIX] 🖱️ Clicked selector.")
        
        # 2. Wait for Options (cdk-overlay or sidebar)
        print("[FIX] ⏳ Waiting for 'Model selection' panel...")
        await page.wait_for_selector("text=Model selection", timeout=5000)
        
        # Dump HTML to find card selectors
        print("[FIX] 📸 Dumping panel HTML...")
        with open("debug_model_panel.html", "w") as f:
            f.write(await page.content())
            
        # Try to find "Gemini 3.1 Pro Preview" or similar
        # We'll try a broad text match click for now
        try:
            print("[FIX] 🎯 Clicking 'Gemini 3.1 Pro Preview'...")
            # Use specific locator for the card if possible, otherwise text
            # Often the card is a button
            await page.click("text=Gemini 3.1 Pro Preview", timeout=2000)
            await asyncio.sleep(1)
        except:
             print("[FIX] ⚠️ Text click failed. Trying generic button in list...")
             
        
        await asyncio.sleep(2)
        
        # 3. Retry Prompt
        print("[FIX] 🔄 Retrying prompt with new model...")
        textarea = page.locator("textarea")
        await textarea.fill("Hello Gemini 1.5")
        await page.keyboard.press("Control+Enter")
        
        await asyncio.sleep(5)
        
        # Check success
        # Look for the last chunk and ensure it has text
        chunks = page.locator("ms-text-chunk")
        count = await chunks.count()
        if count > 0:
            text = await chunks.last.inner_text()
            print(f"[FIX] ✅ SUCCESS! Response: '{text}'")
            if len(text) < 2:
                print("[FIX] ⚠️ Response is suspiciously short/empty.")
        else:
            print("[FIX] ❌ No chunks found.")
            
        await page.screenshot(path="debug_fix_model_v2.png")
        await context.close()

if __name__ == "__main__":
    asyncio.run(change_model())
