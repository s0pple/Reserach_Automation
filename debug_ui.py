import asyncio
import json
from playwright.async_api import async_playwright
from src.modules.browser.profile_manager import BrowserProfileManager

async def debug_gemini_ui():
    pm = BrowserProfileManager()
    user_data_dir = pm.get_profile_path("main")
    
    print(f"🚀 Starte UI-Scanner mit Profil: {user_data_dir}")
    
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False, # Wir wollen sehen, was passiert
            viewport={'width': 1920, 'height': 1080}
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        print("🌐 Navigiere zu Gemini...")
        await page.goto("https://gemini.google.com/app", wait_until="load")
        
        print("⏳ Warte 10 Sekunden auf UI-Elemente...")
        await asyncio.sleep(10)
        
        # Screenshot machen
        await page.screenshot(path="gemini_ui_debug.png")
        print("📸 Screenshot gespeichert: gemini_ui_debug.png")
        
        # Alle Buttons scannen
        print("🔍 Scanne Button-DNA...")
        buttons_data = await page.evaluate("""
            () => {
                const btns = Array.from(document.querySelectorAll('button, [role="button"], .mat-mdc-button-touch-target'));
                return btns.map(b => {
                    const rect = b.getBoundingClientRect();
                    return {
                        text: b.innerText.trim(),
                        aria_label: b.getAttribute('aria-label'),
                        classes: b.className,
                        id: b.id,
                        is_visible: rect.width > 0 && rect.height > 0,
                        html_tag: b.tagName
                    };
                }).filter(b => b.text.length > 0 || b.aria_label);
            }
        """)
        
        with open("gemini_ui_dna.json", "w", encoding="utf-8") as f:
            json.dump(buttons_data, f, indent=2)
            
        print("✅ UI-DNA gespeichert: gemini_ui_dna.json")
        await context.close()

if __name__ == "__main__":
    asyncio.run(debug_gemini_ui())
