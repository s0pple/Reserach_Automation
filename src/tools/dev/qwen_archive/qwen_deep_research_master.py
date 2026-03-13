import asyncio
import os
import time
from playwright.async_api import async_playwright
from src.tools.cv_bot.workflow_manager import WorkflowManager

async def run_ultimate_victory():
    os.environ["DISPLAY"] = ":99"
    manager = WorkflowManager()
    
    async with async_playwright() as p:
        print("🌐 Launching Chromium (Ultimate Victory Mode)...")
        browser = await p.chromium.launch(headless=False, args=["--no-sandbox", "--disable-dev-shm-usage"])
        context = await browser.new_context(viewport={'width': 1280, 'height': 1024})
        page = await context.new_page()
        
        await page.goto('https://chat.qwen.ai/', wait_until='networkidle')
        await asyncio.sleep(5)
        
        # 1. CSS-KILL (Anti-Banner)
        await page.add_style_tag(content="[class*='banner'], [class*='overlay'] { display: none !important; }")
        
        # 2. PROMPT
        prompt = "Führe eine Marktanalyse zur KI-Infrastruktur 2030 durch. Sei extrem ausführlich."
        await page.locator("textarea").first.fill(prompt)
        await asyncio.sleep(1)
        await page.keyboard.press("Enter")
        print("🚀 Prompt sent. Waiting for Login-Modal...")
        await asyncio.sleep(4)
        
        # 3. STAY LOGGED OUT (Visueller Klick via CV-Bot)
        print("🔍 Searching for 'Stay logged out' button...")
        image_bytes, img_bgra, ox, oy = manager._get_screenshot_bytes()
        res_stay = await manager.cv_tool.find_element_via_vision(image_bytes, "the 'Stay logged out' button or link", original_bgra=img_bgra, offset_x=ox, offset_y=oy)
        
        if res_stay.get("found"):
            print(f"🖱️ Clicking 'Stay logged out' at {res_stay['x']}, {res_stay['y']}")
            await page.mouse.click(res_stay['x'], res_stay['y'])
            await asyncio.sleep(2)
            # Nochmal Enter für den Prompt falls nötig
            await page.keyboard.press("Enter")
        else:
            print("⚠️ 'Stay logged out' not found visually. Trying DOM search...")
            try:
                stay_btn = page.locator("text='Stay logged out'").first
                if await stay_btn.is_visible():
                    await stay_btn.click()
                    print("✅ Clicked 'Stay logged out' via DOM.")
            except:
                pass

        # 4. WARTEN & EXTRAKTION
        print("⏳ Waiting 60s for response...")
        await asyncio.sleep(60)
        
        report = await page.evaluate("""() => {
            const bubbles = document.querySelectorAll('[class*="message-content"], [class*="content"]');
            return Array.from(bubbles).map(b => b.innerText).join('\\n\\n--- NEXT --- \\n\\n');
        }""")
        
        with open("test/qwen_ULTRALORD_REPORT.md", "w", encoding="utf-8") as f:
            f.write(report)
            
        print(f"🎉 DONE! Report size: {len(report)} chars.")
        await page.screenshot(path="test/qwen_final_proof.png")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_ultimate_victory())
