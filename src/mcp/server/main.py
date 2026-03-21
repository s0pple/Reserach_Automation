import os
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict

import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

from src.core.ai_studio_controller import AIStudioController

@dataclass
class BrowserTask:
    session_id: str
    action: str
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    system_instruction: Optional[str] = None
    future: asyncio.Future = None

task_queue: asyncio.Queue = asyncio.Queue()

class TabRegistry:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.controllers: Dict[str, AIStudioController] = {}
        self.max_tabs = 3
        self.account_id = os.getenv('ACCOUNT_ID', 'default_acc')

    async def get_or_create_controller(self, session_id: str) -> AIStudioController:
        if not self.playwright:
            self.playwright = await async_playwright().start()

        if not self.context:
            profile_path = f'/app/data/browser_sessions/{self.account_id}'
            print(f'[TabRegistry] Lade 1-CONTAINER Context fuer {self.account_id}...')
            self.context = await self.playwright.chromium.launch_persistent_context(
                user_data_dir=profile_path,
                headless=False,
                viewport={'width': 1280, 'height': 720},
                args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
            )

        if session_id in self.controllers:
            return self.controllers[session_id]

        if len(self.controllers) >= self.max_tabs:
            raise RuntimeError(f'RAM-Schutz aktiv. Maximum {self.max_tabs} erreicht.')

        if len(self.controllers) == 0 and len(self.context.pages) > 0:
            page = self.context.pages[0]
        else:
            page = await self.context.new_page()
            
        controller = AIStudioController(page)
        print(f'[TabRegistry] Initialisiere Session in TAB fuer {session_id}')
        await controller.init_session()
        self.controllers[session_id] = controller
        return controller

tab_registry = TabRegistry()

async def browser_worker_loop():
    print('?? [Worker] Maus-Gott Loop gestartet...')
    while True:
        task: BrowserTask = await task_queue.get()
        print(f'[Worker] Task gepickt: Session {task.session_id} | {task.action}')

        try:
            async with asyncio.timeout(90.0):
                controller = await tab_registry.get_or_create_controller(task.session_id)
                await controller.page.bring_to_front()
                await controller.page.wait_for_timeout(500)

                if task.action == 'generate':
                    if task.model_name:
                        await controller.set_model(task.model_name)
                    await controller.send_prompt(task.prompt)
                    response = await controller.wait_for_response()
                    task.future.set_result(response)
                else:
                    raise ValueError(f'Unbekannte Aktion: {task.action}')

        except TimeoutError:
            err_msg = f'Timeout (> 90s) fuer Session: {task.session_id}.'
            print(err_msg)
            task.future.set_exception(Exception(err_msg))
        except Exception as e:
            print(f'Fehler: {e}')
            task.future.set_exception(e)
        finally:
            print(f'Task fuer Session {task.session_id} beendet. Lock frei.')
            task_queue.task_done()

mcp = FastMCP('Browser-Hub-God-Container')

@mcp.tool()
async def ask_gemini(session_id: str, prompt: str, model_name: str = 'Gemini 3.1 Pro Preview') -> str:
    loop = asyncio.get_running_loop()
    future = loop.create_future()
    queue_pos = task_queue.qsize()
    print(f'[MCP] Task fuer {session_id} auf pos {queue_pos}')

    task = BrowserTask(
        session_id=session_id, action='generate', prompt=prompt,
        model_name=model_name, future=future
    )
    await task_queue.put(task)
    try:
        return await future
    except Exception as e:
        return f'Worker failed: {str(e)}'

app = FastAPI()

@app.on_event('startup')
async def startup_event():
    asyncio.create_task(browser_worker_loop())

@app.get('/health')
async def health_check():
    return {
        'status': 'online',
        'queue_size': task_queue.qsize(),
        'active_sessions': list(tab_registry.controllers.keys()),
        'max_tabs_allowed': tab_registry.max_tabs,
        'container_account': tab_registry.account_id
    }

app.mount('/', mcp.sse_app())

if __name__ == '__main__':
    PORT = int(os.getenv('PORT', 8000))
    print('=' * 60)
    print(f'?? Starte God-Container Browser Hub Port {PORT}')
    print('=' * 60)
    uvicorn.run(app, host='0.0.0.0', port=PORT)
