import os
import asyncio
import sys
import json
import time
from typing import Optional, Dict, Any
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

# ARE: Monkeypatch MCP Security for Docker Service-to-Service communication
import mcp.server.transport_security
async def skip_validation(self, request, is_post=False): return None
try:
    mcp.server.transport_security.TransportSecurityMiddleware.validate_request = skip_validation
    print("📡 [Iron Fortress] MCP DNS Rebinding Protection: BYPASSED.")
except:
    pass

from src.core.ai_studio_controller import AIStudioController

# Global Registry & Lock for Single-Task Execution per Container
class IronFortressHub:
    def __init__(self):
        self.playwright = None
        self.browser = None
        self.page = None
        self.lock = asyncio.Lock()
        self.account_id = os.getenv('ACCOUNT_ID', 'default_acc')
        self.data_dir = os.getenv("DATA_DIR", "data")

    async def close_browser(self):
        if self.browser:
            try: await self.browser.close()
            except: pass
            self.browser = None
            self.page = None
        if self.playwright:
            try: await self.playwright.stop()
            except: pass
            self.playwright = None

    async def get_page(self):
        if not self.playwright or not self.browser or not self.page or self.page.is_closed():
            print("🌐 [MCP] Initializing fresh browser context...")
            await self.close_browser()
            
            self.playwright = await async_playwright().start()
            profile_path = os.path.join(self.data_dir, 'browser_sessions', self.account_id)
            os.makedirs(profile_path, exist_ok=True)
            
            # Clean SingletonLock
            lock_path = os.path.join(profile_path, "SingletonLock")
            if os.path.exists(lock_path):
                try: os.remove(lock_path)
                except: pass

            self.browser = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=False,
                args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-blink-features=AutomationControlled", "--disable-infobars"]
            )
            # Ensure at least one page exists
            if not self.browser.pages:
                await self.browser.new_page()
            self.page = self.browser.pages[0]
            
        return self.page

hub = IronFortressHub()
mcp = FastMCP('Iron-Fortress-Server')

@mcp.tool()
async def ask_gemini(prompt: str, session_id: str = "default", request_id: str = "N/A") -> str:
    """Sends a research prompt to Gemini via AI Studio with per-container task locking."""
    print(f"🎬 [MCP] Tool Call: ask_gemini (req:{request_id}, sess:{session_id})")
    
    async with hub.lock:
        try:
            page = await hub.get_page()
            
            # Resetting page state if previous task failed miserably
            if not page or page.is_closed():
                hub.page = None
                page = await hub.get_page()

            controller = AIStudioController(page, request_id=request_id, session_id=session_id)
            
            # Safety Wrapper for 500 Errors
            for attempt in range(2):
                await controller.init_session()
                await controller.ensure_fresh_chat()
                
                # Check if still errored
                error_msg = page.get_by_text("An internal error has occurred").first
                if await error_msg.count() == 0:
                    break
                
                print(f"🔄 [MCP] Persistent 500 error on attempt {attempt+1}. IP or Session might be hot.")
                await asyncio.sleep(10) # Cooling between reloads
            
            # Strike Limit Reached - Need Hard Restart
            error_msg = page.get_by_text("An internal error has occurred").first
            if await error_msg.count() > 0 and await error_msg.is_visible():
                print("🚨 [MCP] HARD LIMIT REACHED. CLOSING BROWSER.")
                await hub.close_browser()
                raise RuntimeError("AI Studio stuck in 500 error after 2 reloads. Context reset triggered.")

            # 2. Research
            await controller.send_prompt(prompt)
            result = await controller.wait_for_response()
            
            return str(result)
        except Exception as e:
            print(f"🚨 [MCP] Tool Error: {e}")
            # Ensure browser doesn't stay in bad state for next tool call
            if "Timeout" in str(e) or "reset" in str(e).lower():
                print("🧹 [MCP] Closing browser after fatal error/timeout.")
                await hub.close_browser()
            return json.dumps({"status": "error", "details": str(e)})

@mcp.tool()
async def ask_chatgpt(prompt: str, session_id: str = "default", model_name: str = "gpt-4o", request_id: str = "N/A") -> str:
    """Universal Alias for OpenAI-style routing."""
    return await ask_gemini(prompt, session_id=session_id, request_id=request_id)

@mcp.tool()
async def ask_browser_agent(prompt: str, session_id: str = "default", model_name: str = "browser-agent", request_id: str = "N/A") -> str:
    """Universal Alias for Agentic-style routing."""
    return await ask_gemini(prompt, session_id=session_id, request_id=request_id)

if __name__ == "__main__":
    # ARE Hardening: Bind the FastMCP SSE application to 0.0.0.0:8000
    import uvicorn
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=8000)
