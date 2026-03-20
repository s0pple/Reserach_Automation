import asyncio
import os
from playwright.async_api import async_playwright, Page, expect

# --- CONFIGURATION ---
PROFILE_PATH = "/app/browser_sessions/account_cassie"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

# --- SELECTORS (Verified via HTML Dump) ---
INPUT_SELECTOR = "textarea[aria-label='Enter a prompt']"
RUN_BUTTON_SELECTOR = "button[aria-label='Run']" 
# ms-text-chunk is the standard for streamed text in AI Studio/Gemini
RESPONSE_SELECTOR = "ms-text-chunk" 
# Fallback if ms-text-chunk isn't found (e.g. error message or different view)
RESPONSE_FALLBACK = ".model-turn, .turn-content"

async def ask_ai_studio(page: Page, prompt: str) -> str:
    """
    Sends a prompt to AI Studio and waits for the full response using robust state monitoring.
    """
    print(f"\n[AI-STUDIO] 🟢 Prompt: '{prompt[:40]}...'")

    # 1. Wait for Input and Fill
    try:
        input_box = page.locator(INPUT_SELECTOR)
        await input_box.wait_for(state="visible", timeout=10000)
        await input_box.fill(prompt)
    except Exception as e:
        raise Exception(f"Input box not found ({INPUT_SELECTOR}): {e}")

    # 2. Get Run Button Reference
    run_button = page.locator(RUN_BUTTON_SELECTOR).first
    
    # 3. Trigger Generation (Ctrl+Enter is most reliable)
    await page.keyboard.press("Control+Enter")
    print("[AI-STUDIO] 🚀 Sent (Ctrl+Enter)")

    # 4. Wait for Streaming START (Button might Disappear OR Disable)
    print("[AI-STUDIO] ⏳ Waiting for stream to START...")
    try:
        # Check if it disappears (replaced by Stop button) or becomes disabled
        # We race these conditions or just check sequentially
        await expect(run_button).to_be_disabled(timeout=5000)
        print("[AI-STUDIO] Run button disabled (Stream started).")
    except:
        try:
             # If it didn't disable, did it disappear?
            await expect(run_button).to_be_hidden(timeout=5000)
            print("[AI-STUDIO] Run button hidden (Stream started).")
        except:
             print("[AI-STUDIO] ⚠️ Warning: Run button state didn't change. Response might be instant.")

    # 5. Wait for Streaming END (Button must return and be Enabled)
    print("[AI-STUDIO] ⏳ Waiting for stream to END (Button -> Visible & Enabled)...")
    # Long timeout for Deep Research tasks
    await run_button.wait_for(state="visible", timeout=120000)
    await expect(run_button).not_to_be_disabled(timeout=5000)
    print("[AI-STUDIO] ✅ Stream finished.")

    # 6. Extract Response
    # We assume the last text chunk is the new response.
    # We wait a brief moment for the DOM to settle (sometimes text renders after button enables)
    await asyncio.sleep(0.5)
    
    chunks = page.locator(RESPONSE_SELECTOR)
    count = await chunks.count()
    
    if count > 0:
        # Get the text of the LAST chunk
        last_chunk = chunks.nth(count - 1)
        text = await last_chunk.inner_text()
        print(f"[AI-STUDIO] 📄 Extracted {len(text)} chars from last chunk.")
        return text
    else:
        # Fallback
        print("[AI-STUDIO] ⚠️ No 'ms-text-chunk' found. Trying fallback selectors...")
        fallback = page.locator(RESPONSE_FALLBACK).last
        if await fallback.count() > 0:
            text = await fallback.inner_text()
            print(f"[AI-STUDIO] 📄 Extracted {len(text)} chars from fallback.")
            return text
        else:
            # Last Resort: Dump the whole chat container
            print("[AI-STUDIO] ❌ No response elements found. Dumping body text for debug.")
            return "ERROR: Could not find response text."

async def main():
    async with async_playwright() as p:
        args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        # Ensure generic Xvfb display if not set
        if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
        
        print(f"[AI-STUDIO] 🌍 Launching Browser (Profile: {PROFILE_PATH})...")
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=False, # Keeping it visible for Xvfb/Screenshots
            args=args,
            viewport={"width": 1280, "height": 800}
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        print(f"[AI-STUDIO] 🔗 Navigating to {AI_STUDIO_URL}...")
        await page.goto(AI_STUDIO_URL)
        
        # Check if we are logged in (look for generic Google account indicator)
        try:
            # e.g. "Sign in" button would be bad. 
            # We assume the profile handles it, but let's wait a bit.
            await page.wait_for_selector(INPUT_SELECTOR, timeout=15000)
            print("[AI-STUDIO] ✅ Ready (Input field visible).")
        except:
            print("[AI-STUDIO] ❌ Login Check Failed! Input field not found.")
            # Take a screenshot for debug
            await page.screenshot(path="debug_login_fail.png")
            print("Saved debug_login_fail.png")
            await context.close()
            return

        # --- TEST LOOP ---
        prompts = [
            "What is the capital of France?",
            "Count to 5.",
            "Explain Quantum Computing in one sentence."
        ]
        
        for i, prompt in enumerate(prompts):
            print(f"\n--- TEST {i+1}/{len(prompts)} ---")
            response = await ask_ai_studio(page, prompt)
            print(f"RESPONSE: {response}")
            await asyncio.sleep(2) # Cooldown

        print("\n[AI-STUDIO] 🎉 All tests completed.")
        await context.close()

if __name__ == "__main__":
    asyncio.run(main())
