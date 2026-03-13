import asyncio
import os
import sys
from playwright.async_api import async_playwright
from src.modules.browser.profile_manager import BrowserProfileManager

async def setup_session(persona: str):
    profile_manager = BrowserProfileManager()
    user_data_dir = profile_manager.get_profile_path(persona)
    
    print(f"🚀 Launching Chrome for Manual Login...")
    print(f"👤 Persona: {persona.upper()}")
    print(f"📂 Session Data Folder: {user_data_dir}")
    print("\n[INSTRUCTIONS]")
    print("1. A browser window will open.")
    print("2. Log in to your Google Account on gemini.google.com.")
    print("3. IMPORTANT: Once logged in, DO NOT close the window yet.")
    print("4. Come back here and press ENTER to save and close properly.")

    async with async_playwright() as p:
        # Launch VISIBLE browser
        context = await p.chromium.launch_persistent_context(
            user_data_dir=user_data_dir,
            headless=False, 
            viewport={'width': 1280, 'height': 900},
            args=["--disable-blink-features=AutomationControlled"]
        )
        page = await context.new_page()
        
        # Go to Gemini Web
        await page.goto("https://gemini.google.com/app")
        
        input("\n👉 Press ENTER here once you have successfully logged in...")
        
        await context.close()
        print(f"✅ Session for '{persona}' saved successfully!")

if __name__ == "__main__":
    # Default to 'main' if no persona is passed
    persona_arg = sys.argv[1] if len(sys.argv) > 1 else "main"
    asyncio.run(setup_session(persona_arg))
