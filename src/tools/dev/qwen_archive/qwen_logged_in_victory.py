import asyncio
import os
import time
from playwright.async_api import async_playwright

async def run_logged_in_victory():
    os.environ["DISPLAY"] = ":99"
    # Absoluter Pfad zu unserem Google-Profil im Container
    profile_dir = os.path.abspath("browser_sessions/google_searcher")
    
    async with async_playwright() as p:
        print(f"🌐 Launching Chromium with Profile: {profile_dir}...")
        # Wir nutzen launch_persistent_context um das Google-Profil zu laden
        context = await p.chromium.launch_persistent_context(
            user_data_dir=profile_dir,
            headless=False,
            args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.set_viewport_size({"width": 1280, "height": 1024})
        
        print("🚀 Navigating to Qwen with Google Login Session...")
        await page.goto('https://chat.qwen.ai/', wait_until='networkidle')
        await asyncio.sleep(8)
        
        # 1. VISUAL CHECK (Sollte kein Banner sein, aber zur Sicherheit CSS-Kill)
        await page.add_style_tag(content="[class*='banner'], [class*='overlay'] { display: none !important; }")
        await page.screenshot(path="test/qwen_logged_in_state.png")
        
        # 2. PROMPT INJEKTION & SEND
        prompt = "FÜHRE EIN DEEP RESEARCH DURCH: Zukunft der KI-Infrastruktur 2030. Analysiere Hardware, Energie und Software. Erstelle einen extrem langen Bericht."
        print(f"⌨️ Typing prompt into chat...")
        
        try:
            # Suche Eingabefeld
            await page.locator("textarea, [contenteditable='true']").first.fill(prompt)
            await asyncio.sleep(1)
            await page.keyboard.press("Enter")
            print("🚀 Prompt sent! Waiting for generation (2 minutes)...")
            
            # 3. WARTEN & EXTRAKTION
            # Wir warten 2 Minuten für den vollen Deep Research Bericht
            for i in range(4):
                await asyncio.sleep(30)
                await page.screenshot(path=f"test/qwen_research_step_{i}.png")
                print(f"⏳ Researching... ({ (i+1)*30 }s)")

            print("📋 Final extraction...")
            report = await page.evaluate("""() => {
                const messages = document.querySelectorAll('[class*="message-content"], [class*="content"]');
                return Array.from(messages).map(m => m.innerText).join('\\n\\n--- SECTION ---\\n\\n');
            }""")
            
            with open("test/qwen_LOGGED_IN_FINAL_REPORT.md", "w", encoding="utf-8") as f:
                f.write(f"# Qwen Final Logged-in Victory Report\n\n{report}")
            
            print(f"🎉 MISSION SUCCESS! Report saved. Size: {len(report)} chars.")
            await page.screenshot(path="test/qwen_VICTORY_FULL.png")
            
        except Exception as e:
            print(f"❌ Error during execution: {e}")
            await page.screenshot(path="test/qwen_error_state.png")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(run_logged_in_victory())
