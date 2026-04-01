import os
import asyncio
import sys
import json
import time
import threading
import uvicorn
from dataclasses import dataclass
from typing import Optional, Dict, Any
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

# ARE: Monkeypatch MCP Security for Docker Service-to-Service communication
import mcp.server.transport_security
async def skip_validation(self, request, is_post=False): return None
mcp.server.transport_security.TransportSecurityMiddleware.validate_request = skip_validation
print("📡 [Iron Fortress] MCP DNS Rebinding Protection: BYPASSED.")

# Core components
from src.core.ai_studio_controller import AIStudioController
try:
    from tests.chaos_driver import ChaosDriver
except:
    class ChaosDriver:
        def __init__(self, page): self.page = page
        async def simulate_half_open_modal(self): pass

@dataclass
class BrowserTask:
    session_id: str
    action: str
    request_id: str = "N/A"
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    future: Any = None 

# Global queue and loop reference for thread-safe communication
task_queue: Optional[asyncio.Queue] = None
worker_loop: Optional[asyncio.AbstractEventLoop] = None

DATA_DIR = os.getenv("DATA_DIR", "data")
os.makedirs(DATA_DIR, exist_ok=True)

class TabRegistry:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.controllers: Dict[str, Any] = {}
        self.max_tabs = 1
        self.account_id = os.getenv('ACCOUNT_ID', 'default_acc')

    async def get_or_create_controller(self, session_id: str, request_id: str = "N/A") -> Any:
        if not self.playwright: self.playwright = await async_playwright().start()
        if not self.context:
            profile_path = os.path.join(DATA_DIR, 'browser_sessions', self.account_id)
            lock_path = os.path.join(profile_path, "SingletonLock")
            if os.path.exists(lock_path):
                try: os.remove(lock_path)
                except: pass
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path, headless=False,
                viewport={'width': 1280, 'height': 720},
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
            )
            self.controllers = {}

        if session_id in self.controllers: return self.controllers[session_id]
        page = self.context.pages[0] if self.context.pages else await self.context.new_page()
        controller = AIStudioController(page, request_id=request_id, session_id=session_id)
        await controller.init_session()
        self.controllers[session_id] = controller
        return controller

tab_registry = TabRegistry()

async def browser_worker_loop_task():
    global task_queue
    task_queue = asyncio.Queue()
    print('🚀 [Worker] Iron Fortress Loop Active (Threaded).')
    while True:
        try:
            task: BrowserTask = await task_queue.get()
            request_id = task.request_id
            
            try:
                async with asyncio.timeout(600.0):
                    controller = await tab_registry.get_or_create_controller(task.session_id, request_id=request_id)
                    await controller.ensure_fresh_chat()
                    
                    # Chaos Engine Detection
                    sabotage = os.getenv("CHAOS_SABOTAGE")
                    if sabotage == "half_open_modal":
                        chaos = ChaosDriver(controller.page)
                        await chaos.simulate_half_open_modal()

                    await controller.send_prompt(task.prompt)
                    response = await controller.wait_for_response()
                    
                    # V15 Fix: Return raw response to avoid Double-JSON encoding in proxy
                    result_text = f"{response}"
                    if not task.future.done():
                        task.future.get_loop().call_soon_threadsafe(task.future.set_result, result_text)
            except Exception as e:
                err = {"status": "error", "details": str(e)}
                if not task.future.done():
                    task.future.get_loop().call_soon_threadsafe(task.future.set_result, json.dumps(err))
            finally:
                task_queue.task_done()
        except Exception as e:
            print(f"⚠️ Worker Error: {e}")
            await asyncio.sleep(2)

def start_worker_thread():
    global worker_loop
    worker_loop = asyncio.new_event_loop()
    asyncio.set_event_loop(worker_loop)
    worker_loop.run_until_complete(browser_worker_loop_task())

mcp = FastMCP('Browser-Hub-God-Container')

@mcp.tool()
async def ask_gemini(session_id: str, prompt: str, model_name: str = 'Gemini 3.1 Pro Preview', request_id: str = "N/A") -> str:
    """Agentic Tool: Sends a prompt to AI Studio and returns the browser's response."""
    if task_queue is None or worker_loop is None:
        return "Error: Worker Thread not initialized."

    loop = asyncio.get_running_loop()
    future = loop.create_future()
    
    task = BrowserTask(
        session_id=session_id, action='generate', request_id=request_id,
        prompt=prompt, model_name=model_name, future=future
    )
    
    # Thread-safe put into the worker loop's queue
    worker_loop.call_soon_threadsafe(task_queue.put_nowait, task)
    return await future

@mcp.tool()
async def write_research_file(filename: str, content: str) -> str:
    """Agentic Tool: Saves research data (CSV, JSON, etc) to the persistent output directory."""
    try:
        # Sanitize filename (basic)
        safe_name = os.path.basename(filename)
        out_dir = os.path.join("/app", "output")
        os.makedirs(out_dir, exist_ok=True)
        path = os.path.join(out_dir, safe_name)
        
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        
        print(f"💾 [Iron Fortress] File saved: {path}")
        return f"Success: File saved to {filename}"
    except Exception as e:
        return f"Error: Failed to save file: {str(e)}"

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8000))
    print(f'🏰 Starting Port {PORT} on 0.0.0.0')
    # Start the worker in a separate thread
    threading.Thread(target=start_worker_thread, daemon=True).start()
    # MANUALLY RUN THE SSE APP ON 0.0.0.0 (Essential for Docker Network reachability)
    uvicorn.run(mcp.sse_app, host="0.0.0.0", port=PORT)
