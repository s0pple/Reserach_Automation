import os
import time
from playwright.sync_api import sync_playwright

def setup():
    # Ensure directory exists
    os.makedirs("browser_sessions/google_main", exist_ok=True)
    
    with sync_playwright() as p:
        print("Launching Browser for Login...")
        # User defined: browser_sessions/google_main
        context = p.chromium.launch_persistent_context(
            user_data_dir="browser_sessions/google_main",
            headless=False,
            channel="chrome", # Try to use installed chrome if available, else standard chromium
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        
        page = context.new_page()
        page.goto("https://aistudio.google.com/app/prompts/new_chat")
        
        print("\n" + "="*50)
        print("ACTION REQUIRED: Log in to Google manually in the browser window.")
        print("Once logged in and you see the AI Studio interface, close the browser window.")
        print("The session cookies will be saved automatically.")
        print("="*50 + "\n")
        
        # Keep alive until user closes
        try:
            page.wait_for_timeout(300000) # 5 minutes timeout or manual close
        except:
            pass
        
        context.close()
        print("Session saved to browser_sessions/google_main")

if __name__ == "__main__":
    setup()
