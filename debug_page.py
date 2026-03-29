"""
Diagnostics: Dump page selectors for AI Studio response detection.
Run INSIDE the container: python3 /app/debug_page.py
"""
import asyncio
import re
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        # Shared persistent session (read-only access)
        context = await p.chromium.launch_persistent_context(
            user_data_dir='/tmp/debug_session',
            headless=False,
            args=['--no-sandbox', '--disable-dev-shm-usage', '--display=:99']
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        print(f"[DEBUG] Navigating to AI Studio...")
        await page.goto("https://aistudio.google.com/app/prompts/new_chat", wait_until="networkidle")
        await asyncio.sleep(8)
        print(f"[DEBUG] URL: {page.url}")
        
        # Dump all custom elements (Angular/Web Component selectors)
        all_tags = await page.evaluate("""() => {
            const tags = new Set();
            document.querySelectorAll('*').forEach(el => tags.add(el.tagName.toLowerCase()));
            return [...tags].filter(t => t.includes('-')).sort(); // custom elements have dashes
        }""")
        print(f"\n[DEBUG] Custom element tags found on page:")
        for tag in all_tags:
            print(f"  <{tag}>")
        
        # Also check for specific patterns
        checks = [
            ".model-turn", "model-turn", "ms-text-chunk", "ms-chat-turn",
            ".message-content", "message-content", ".response-container",
            "chat-message", ".ai-response", "[class*='model']", "[class*='response']"
        ]
        print(f"\n[DEBUG] Selector probe:")
        for sel in checks:
            try:
                count = await page.locator(sel).count()
                print(f"  [{count:3d}] {sel}")
            except Exception as e:
                print(f"  [ERR] {sel}: {e}")
        
        await context.close()
        print("\n[DEBUG] Done.")

asyncio.run(main())
