import asyncio
import time
from playwright.async_api import async_playwright, Page
from src.modules.browser.profile_manager import BrowserProfileManager

class AIStudioProvider:
    """
    Automates Google AI Studio (aistudio.google.com) to act as the "Brain" 
    without needing API keys.
    """
    def __init__(self, headless: bool = False, persona: str = "brain"):
        self.headless = headless
        self.persona = persona
        self.profile_manager = BrowserProfileManager()
        self.user_data_dir = self.profile_manager.get_profile_path(persona)
        self.playwright = None
        self.context = None
        self.page = None

    async def start_session(self):
        self.playwright = await async_playwright().start()
        self.context = await self.playwright.chromium.launch_persistent_context(
            user_data_dir=self.user_data_dir,
            headless=self.headless,
            viewport={'width': 1280, 'height': 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox"
            ]
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        self.page.set_default_timeout(45000)
        
        print(f"[Brain] 🧠 Navigating to Google AI Studio...")
        await self.page.goto("https://aistudio.google.com/app/prompts/new_chat", wait_until="load")
        
        # Check for login
        if "accounts.google.com" in self.page.url:
            print(f"[Brain] 🔑 Login required for AI Studio! Please log in manually.")
            if not self.headless:
                await self.page.wait_for_url("**/app/prompts**", timeout=300000)
                print("[Brain] ✅ Logged into AI Studio.")
            else:
                raise Exception("AI Studio requires login. Run with visible=True first.")
                
        await asyncio.sleep(5) # Wait for app to fully load

    async def chat(self, message: str) -> str:
        if not self.page:
            raise Exception("Session not started. Call start_session() first.")
            
        print("[Brain] ✍️ Entering message into AI Studio...")
        
        # Try to find the chat input. AI studio uses a contenteditable div or textarea.
        # We try a broad evaluate approach to inject the text
        await self.page.evaluate("""
            (text) => {
                // Find input area. In AI studio it's often a textarea with placeholder "Type something" or a specific element
                const inputs = Array.from(document.querySelectorAll('textarea, input[type="text"], [contenteditable="true"]'));
                // Filter out non-visible or small inputs
                const chatInput = inputs.find(el => el.clientHeight > 20 && !el.disabled) || inputs[inputs.length - 1];
                
                if (chatInput) {
                    if (chatInput.tagName === 'TEXTAREA' || chatInput.tagName === 'INPUT') {
                        chatInput.value = text;
                    } else {
                        chatInput.innerText = text;
                    }
                    chatInput.dispatchEvent(new Event('input', { bubbles: true }));
                }
            }
        """, message)
        
        await asyncio.sleep(1)
        
        # Click the send/run button
        print("[Brain] ⚡ Sending message...")
        try:
            # AI Studio typically has a "Run" button or standard send icon
            send_btn = self.page.locator('button:has-text("Run"), button[aria-label*="Run"], button[aria-label*="Send"], ms-icon:has-text("send")').first
            if await send_btn.is_visible(timeout=3000):
                await send_btn.click()
            else:
                await self.page.keyboard.press("Enter") # fallback
                # sometimes it requires cmd+enter or ctrl+enter
                await self.page.keyboard.down("Control")
                await self.page.keyboard.press("Enter")
                await self.page.keyboard.up("Control")
        except Exception as e:
            print(f"[Brain] ⚠️ Could not find send button, pressed Enter. ({e})")
            
        print("[Brain] ⏳ Waiting for Brain to respond...")
        
        # Wait for the response to finish generating
        # In AI studio, there is usually a stop button while generating
        await asyncio.sleep(5)
        
        is_generating = True
        wait_time = 0
        while is_generating and wait_time < 120:
            try:
                # Check for stop button
                stop_btn = self.page.locator('button:has-text("Stop"), ms-icon:has-text("stop")').first
                if not await stop_btn.is_visible(timeout=2000):
                    is_generating = False
            except:
                is_generating = False
            
            if is_generating:
                await asyncio.sleep(2)
                wait_time += 2
                
        # Give it a second to finalize rendering
        await asyncio.sleep(2)
        
        print("[Brain] 📄 Extracting response...")
        # Extract the last message
        response = await self.page.evaluate("""
            () => {
                // AI Studio messages are usually in blocks. We try to find model responses.
                // This is generic and might need tuning based on exact AI Studio DOM
                const msgs = document.querySelectorAll('.model-message, [class*="message-content"], .message-content');
                if (msgs.length > 0) {
                    return msgs[msgs.length - 1].innerText;
                }
                
                // Fallback: Just grab the whole chat area text and we'll parse the end
                const chatArea = document.querySelector('main') || document.body;
                return chatArea.innerText;
            }
        """)
        
        return response

    async def close(self):
        if self.context:
            await self.context.close()
        if self.playwright:
            await self.playwright.stop()
