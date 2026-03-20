import asyncio
import os
from playwright.async_api import async_playwright, Page, expect

class AIStudioClient:
    """
    A robust client for Google AI Studio (Web UI).
    Handles streaming, banners, and model switching.
    """
    
    def __init__(self, profile_path="/app/browser_sessions/account_cassie"):
        self.profile_path = profile_path
        self.browser = None
        self.context = None
        self.page = None
        
    async def start(self, headless=False):
        p = await async_playwright().start()
        args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
        
        self.context = await p.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=headless,
            args=args,
            viewport={"width": 1280, "height": 800}
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        
        print("[AI-STUDIO] Navigating to AI Studio...")
        await self.page.goto("https://aistudio.google.com/app/prompts/new_chat")
        await asyncio.sleep(5)
        await self.dismiss_banners()
        
    async def dismiss_banners(self):
        try:
            banners = self.page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
            if await banners.count() > 0:
                await banners.first.click(force=True)
                print("[AI-STUDIO] Banner dismissed.")
                await asyncio.sleep(1)
        except: pass

    async def new_chat(self):
        try:
            btn = self.page.locator("button[aria-label='New chat']")
            if await btn.count() > 0:
                await btn.click()
                await asyncio.sleep(2)
                print("[AI-STUDIO] New Chat started.")
        except: pass

    async def ask(self, prompt: str, timeout=120) -> str:
        """Sends a prompt and returns the full response text."""
        INPUT_BOX = "textarea[aria-label='Enter a prompt']"
        RUN_BUTTON_CANDIDATES = [
            ".run-button",
            "button[aria-label='Run']",
            "button[aria-label='Send prompt']",
            "button:has(span:has-text('Run'))"
        ]
        
        # 1. Fill Input
        await self.page.wait_for_selector(INPUT_BOX, state="visible")
        await self.page.click(INPUT_BOX)
        await self.page.type(INPUT_BOX, prompt, delay=5)
        await self.page.keyboard.press("Space")
        await self.page.keyboard.press("Backspace")
        
        # 2. Find Run Button
        run_btn = None
        for selector in RUN_BUTTON_CANDIDATES:
            if await self.page.locator(selector).count() > 0:
                run_btn = self.page.locator(selector).first
                break
        
        if run_btn:
            await expect(run_btn).not_to_be_disabled(timeout=10000)
            
        # 3. Send
        await self.page.keyboard.press("Control+Enter")
        print(f"[AI-STUDIO] Prompt sent. Waiting for response...")
        await asyncio.sleep(2)
        
        # 4. Wait for Streaming
        if run_btn:
            try:
                # Wait for button to enable again (means finished)
                for _ in range(timeout):
                    if await self.page.locator(".model-error").count() > 0:
                        raise Exception("AI Studio Internal Error detected.")
                    if not await run_btn.is_disabled():
                        break
                    await asyncio.sleep(1)
            except Exception as e:
                print(f"[AI-STUDIO] Wait warning: {e}")

        # 5. Extract
        model_turn = self.page.locator("ms-chat-turn, [data-turn-role='Model']").last
        await model_turn.wait_for(state="visible")
        
        # Poll for text content
        for _ in range(10):
            raw_text = await model_turn.inner_text()
            text = raw_text.replace("Model", "").strip()
            if len(text) > 10:
                return text
            await asyncio.sleep(1)
            
        raise Exception("Failed to extract response text.")

    async def stop(self):
        if self.context:
            await self.context.close()

# Quick Test
if __name__ == "__main__":
    async def test():
        client = AIStudioClient()
        await client.start()
        try:
            response = await client.ask("Hello! Who are you?")
            print(f"\nRESPONSE:\n{response}")
        finally:
            await client.stop()
    asyncio.run(test())
