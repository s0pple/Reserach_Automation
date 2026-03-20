import asyncio
import os
import cv2
import numpy as np
from playwright.async_api import async_playwright, Page, expect
from src.mcp.manager.status import StatusManager

class GeminiBrowser:
    """
    MCP-compliant browser handler for Google AI Studio.
    Supports multi-account switching and status tracking.
    """
    
    def __init__(self, account_id: str, status_manager: StatusManager):
        self.account_id = account_id
        self.status_manager = status_manager
        # Ensure account specific session path: data/browser_sessions/acc_1
        self.profile_path = os.path.abspath(f"data/browser_sessions/{account_id}")
        self.browser = None
        self.context = None
        self.page = None
        
    async def start(self, headless=True):
        print(f"[GeminiBrowser] Starting for account: {self.account_id} (Headless: {headless})")
        
        # Ensure profile dir exists
        os.makedirs(self.profile_path, exist_ok=True)

        p = await async_playwright().start()
        
        # Hardened arguments for Docker/Xvfb stability (copied from aistudio_client.py)
        args = [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--password-store=basic",
            "--use-gl=swiftshader",
            "--disable-software-rasterizer",
            "--disable-background-timer-throttling",
            "--disable-backgrounding-occluded-windows",
            "--disable-renderer-backgrounding",
            "--ignore-certificate-errors",
            "--allow-running-insecure-content",
            "--disable-blink-features=AutomationControlled"
        ]
        
        if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
        
        self.context = await p.chromium.launch_persistent_context(
            user_data_dir=self.profile_path,
            headless=headless,
            args=args,
            viewport={"width": 1280, "height": 800},
            ignore_default_args=["--enable-automation", "--enable-blink-features=IdleDetection"]
        )
        self.page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        
        print("[GeminiBrowser] Navigating to AI Studio...")
        try:
            await self.page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await asyncio.sleep(5)
            await self.dismiss_banners()
        except Exception as e:
            print(f"[GeminiBrowser] Startup navigation failed: {e}")
            await self.stop()
            raise e
        
    async def dismiss_banners(self):
        try:
            banners = self.page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
            if await banners.count() > 0:
                await banners.first.click(force=True)
                print("[GeminiBrowser] Banner dismissed.")
                await asyncio.sleep(1)
        except: pass

    async def generate(self, prompt: str, timeout=120) -> str:
        """Core MCP function: Sends prompt, returns text."""
        try:
            INPUT_BOX = "textarea[aria-label='Enter a prompt']"
            RUN_BUTTON_CANDIDATES = [
                ".run-button", "button[aria-label='Run']", "button[aria-label='Send prompt']"
            ]
            
            # 1. Fill Input
            await self.page.wait_for_selector(INPUT_BOX, state="visible", timeout=30000)
            await self.page.click(INPUT_BOX)
            await self.page.type(INPUT_BOX, prompt, delay=5)
            await self.page.keyboard.press("Control+Enter")
            
            # 2. Wait logic (Simplified for now, can add OpenCV later if needed)
            print(f"[GeminiBrowser] Prompt sent. Waiting...")
            await asyncio.sleep(2)
            
            # Wait for run button to become enabled again (end of generation)
            run_btn = self.page.locator(RUN_BUTTON_CANDIDATES[0]).first # fallback to first candidate
            # Robust wait loop
            for _ in range(timeout):
                if not await run_btn.is_disabled():
                    break
                await asyncio.sleep(1)

            # 3. Extract
            model_turn = self.page.locator("ms-chat-turn, [data-turn-role='Model']").last
            await model_turn.wait_for(state="visible", timeout=10000)
            return await model_turn.inner_text()

        except Exception as e:
            print(f"[GeminiBrowser] Error during generation: {e}")
            # Mark account as possibly limited/broken?
            # self.status_manager.set_status(self.account_id, "cooldown") 
            raise e

    async def stop(self):
        if self.context:
            await self.context.close()
