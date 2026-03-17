import asyncio
import os
import sys
import json
from playwright.async_api import async_playwright

# Config
PROFILE_PATH = "/app/browser_sessions/account_cassie"

async def test_ai_studio_core():
    print("🧪 Starting AI Studio Core Test...")

    async with async_playwright() as p:
        # Use existing Xvfb display if available
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
            # 1. Navigation
            print("🌍 Navigating to AI Studio...")
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await page.wait_for_timeout(5000)
            
            # Check if we are logged in
            if "signin" in page.url or "accounts.google.com" in page.url:
                print("❌ Not logged in! Run setup_cassie.py first.")
                return

            print("✅ Logged in.")

            # 2. Type & Send Test
            print("⌨️  Testing Type & Send...")
            prompt = "This is a TEST. Please respond with exactly this JSON: {\"status\": \"ok\", \"message\": \"I am ready\"}"
            
            # Wait for textarea
            textarea = page.locator("textarea")
            await textarea.wait_for(state="visible", timeout=10000)
            await textarea.fill(prompt)
            print("   -> Typed prompt.")
            
            await page.keyboard.press("Control+Enter")
            print("   -> Sent (Ctrl+Enter).")
            
            # 3. Wait for Response
            print("⏳ Waiting for response...")
            # We need to wait for the "Stop generating" button to disappear OR a new message to appear.
            # A simple wait is okay for a test.
            await page.wait_for_timeout(8000)
            
            # 4. Read Response (The Hard Part)
            print("📖 Reading response...")
            
            # Strategy: Get all text, but also try to identify message bubbles.
            # In AI Studio, responses are often in `markdown-renderer` or specific containers.
            # Let's try to dump the body text first to see what we get.
            
            content = await page.evaluate("document.body.innerText")
            
            print(f"\n--- RAW CONTENT SNAPSHOT (Last 500 chars) ---\n{content[-500:]}\n-----------------------------------------------")
            
            # Attempt JSON extraction
            import re
            json_matches = re.findall(r'\{.*\}', content, re.DOTALL)
            
            if json_matches:
                print(f"✅ FOUND JSON: {json_matches[-1]}")
            else:
                print("❌ NO JSON FOUND in page text.")
                
            # 5. Screenshot for debug
            await page.screenshot(path="temp/test_core_result.png")
            print("📸 Screenshot saved to temp/test_core_result.png")

        except Exception as e:
            print(f"💥 Error: {e}")
            await page.screenshot(path="temp/test_core_error.png")
        finally:
            await context.close()

if __name__ == "__main__":
    asyncio.run(test_ai_studio_core())
