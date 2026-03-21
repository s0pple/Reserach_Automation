import asyncio
import os
from playwright.async_api import async_playwright, expect

# --- CONFIGURATION ---
PROFILE_PATH = "/app/data/browser_sessions/account_baldyboy"
AI_STUDIO_URL = "https://aistudio.google.com/app/prompts/new_chat"

async def test_core():
    print("[CORE] 🟢 Starting Diagnostic Test...")
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=False,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        print(f"[CORE] 🔗 Navigating to {AI_STUDIO_URL}...")
        await page.goto(AI_STUDIO_URL)
        
        # 1. Input
        textarea = page.locator("textarea").first # FIX: Ensure we wait for at least one textarea but target the first if multiple
        try:
            print(f"[CORE] Waiting for you to login manually if needed... Look at VNC!")
            
            # Very long wait (5 minutes) so the user has time to type their password and do 2FA
            await page.wait_for_url("**/prompts/new_chat**", timeout=300000)
            print(f"[CORE] Success! Reached AI Studio Page.")
            
            print(f"[CORE] Current URL is: {page.url} | Title: {await page.title()}")
            await textarea.wait_for(state="visible", timeout=10000)
            await textarea.fill("What is 2+2? Answer in one word.")
            print("[CORE] ✔️ Filled prompt.")
        except Exception as e:
            print(f"[CORE] ❌ Textarea not found or timeout! URL: {page.url} | Error: {e}")
            await page.screenshot(path="temp/debug_notextarea.png")
            with open("temp/debug_notextarea.html", "w", encoding="utf-8") as f:
                f.write(await page.content())
            return

        # 2. Trigger
        run_button = page.locator("button.ctrl-enter-submits")
        await page.keyboard.press("Control+Enter")
        print("[CORE] 🚀 Triggered generation.")

        # 3. Polling Loop
        print("[CORE] 🕵️ Starting Polling Loop (Max 30s)...")
        for i in range(30):
            # Check Run Button State
            is_disabled = await run_button.is_disabled()
            is_visible = await run_button.is_visible()
            
            # Check Stop Button
            stop_btn = page.locator("button[aria-label='Stop generation']") 
            has_stop = await stop_btn.count() > 0 and await stop_btn.is_visible()
            
            # Check Response
            chunks = page.locator("ms-text-chunk")
            chunk_count = await chunks.count()
            
            print(f"[{i:02d}s] Run: {'DISABLED' if is_disabled else 'ENABLED'} | Visible: {is_visible} | Stop: {has_stop} | Chunks: {chunk_count}")

            # Debug logs for chunks
            if chunk_count > 0:
                for j in range(chunk_count):
                    txt = await chunks.nth(j).inner_text()
                    print(f"   - Chunk {j}: '{txt[:50]}...' (Len: {len(txt)})")

            # Capture debug artifacts at 10s if still disabled
            if i == 10 and is_disabled:
                print("[CORE] 📸 capturing debug_stuck_10s.png and html...")
                await page.screenshot(path="debug_stuck_10s.png")
                with open("debug_stuck_10s.html", "w") as f:
                    f.write(await page.content())
            
            if chunk_count > 0 and not is_disabled and not has_stop:
                # Basic check: do we have text in the last chunk?
                last_text = await chunks.last.inner_text()
                if len(last_text.strip()) > 0:
                    print("[CORE] ✅ Success condition met!")
                    print(f"[CORE] RESPONSE: {last_text}")
                    break
                else:
                    print("[CORE] ⚠️ Run enabled but last chunk empty? waiting...")
                
            await asyncio.sleep(1)
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(test_core())
