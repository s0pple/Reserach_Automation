import os
import asyncio
from dataclasses import dataclass
from typing import Optional, Dict, Any

import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright

from src.core.ai_studio_controller import AIStudioController
from src.core.chatgpt_controller import ChatGPTController
from src.core.claude_controller import ClaudeController
from src.core.deepseek_controller import DeepSeekController
from src.core.perplexity_controller import PerplexityController

import json
import time
import re
import tempfile
import shutil

@dataclass
class BrowserTask:
    session_id: str
    action: str
    request_id: str = "N/A"
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    model_provider: Optional[str] = 'AI_STUDIO'
    system_instruction: Optional[str] = None
    future: Optional[asyncio.Future] = None
    retry_count: int = 0

task_queue: asyncio.Queue = asyncio.Queue()

# Iron Fortress: Persistence Layer
DATA_DIR = "/app/data"
QUEUE_FILE = os.path.join(DATA_DIR, "persistent_queue.json")
RESULTS_DIR = os.path.join(DATA_DIR, "results")

os.makedirs(RESULTS_DIR, exist_ok=True)

def atomic_write_json(path, data):
    with tempfile.NamedTemporaryFile('w', dir=os.path.dirname(path), delete=False) as tf:
        json.dump(data, tf)
        temp_name = tf.name
    os.replace(temp_name, path)

def log_task_persistent(task: BrowserTask):
    try:
        tasks = []
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as f: tasks = json.load(f)
        
        # Avoid dups
        if any(t['request_id'] == task.request_id for t in tasks): return
        
        tasks.append({
            "request_id": task.request_id,
            "session_id": task.session_id,
            "prompt": task.prompt,
            "model_name": task.model_name,
            "model_provider": task.model_provider,
            "retry_count": task.retry_count,
            "timestamp": time.time()
        })
        atomic_write_json(QUEUE_FILE, tasks)
    except Exception as e: print(f"[Fortress] Log error: {e}")

def remove_task_persistent(request_id: str):
    try:
        if not os.path.exists(QUEUE_FILE): return
        with open(QUEUE_FILE, 'r') as f: tasks = json.load(f)
        tasks = [t for t in tasks if t['request_id'] != request_id]
        atomic_write_json(QUEUE_FILE, tasks)
    except Exception as e: print(f"[Fortress] Remove error: {e}")

def save_result(request_id: str, data: Any):
    try:
        path = os.path.join(RESULTS_DIR, f"{request_id}.json")
        atomic_write_json(path, data)
    except Exception as e: print(f"[Fortress] Result save error: {e}")

class TabRegistry:
    def __init__(self):
        self.playwright = None
        self.context = None
        self.controllers: Dict[str, Any] = {}
        self.max_tabs = 1
        self.account_id = os.getenv('ACCOUNT_ID', 'default_acc')

    async def _ensure_single_tab(self):
        if not self.context:
            return

        pages = self.context.pages
        while len(pages) > 1:
            print(f"[TabRegistry] Schließe überschüssige Seite ({len(pages)} insgesamt)")
            await pages[-1].close()
            pages = self.context.pages

        if len(pages) == 0:
            print("[TabRegistry] Keine Seite offen, erzeuge neue Seite")
            await self.context.new_page()


    async def get_or_create_controller(self, session_id: str, provider: str = 'AI_STUDIO', request_id: str = "N/A") -> Any:
        try:
            if not self.playwright:
                self.playwright = await async_playwright().start()

            # Self-healing: Re-launch context if it's missing or disconnected
            context_ok = self.context is not None
            if context_ok:
                try:
                    if not self.context.browser or not self.context.browser.is_connected():
                        context_ok = False
                except:
                    context_ok = False
            
            if not context_ok:
                profile_path = f'/app/data/browser_sessions/{self.account_id}'
                print(f'[TabRegistry] LONE-WOLF/RECOVER Lade Context [{self.account_id}]...')
                self.context = await self.playwright.chromium.launch_persistent_context(
                    user_data_dir=profile_path,
                    headless=False,
                    viewport={'width': 1280, 'height': 720},
                    args=['--disable-blink-features=AutomationControlled', '--no-sandbox', '--disable-dev-shm-usage']
                )
                self.controllers = {}

            await self._ensure_single_tab()

            if session_id in self.controllers:
                self.controllers[session_id].request_id = request_id
                return self.controllers[session_id]

            if len(self.controllers) >= self.max_tabs:
                print(f'[TabRegistry] RAM-Schutz: Deleting old controllers...')
                for old_session, old_controller in list(self.controllers.items()):
                    try:
                        await old_controller.page.close()
                    except: pass
                    self.controllers.pop(old_session, None)

            await self._ensure_single_tab()

            if len(self.context.pages) > 0:
                page = self.context.pages[0]
            else:
                page = await self.context.new_page()

            if provider == 'CHATGPT':
                controller = ChatGPTController(page)
            elif provider == 'CLAUDE':
                controller = ClaudeController(page)
            elif provider == 'DEEPSEEK':
                controller = DeepSeekController(page)
            elif provider == 'PERPLEXITY':
                controller = PerplexityController(page)
            else:
                controller = AIStudioController(page, request_id=request_id)
                
            print(f'[TabRegistry] Controller created | REQ: {request_id}')
            await controller.init_session()
            self.controllers[session_id] = controller
            return controller

        except Exception as e:
            err_msg = str(e)
            if "Target closed" in err_msg or "Protocol error" in err_msg or "closed" in err_msg:
                print(f"!!! [TabRegistry] RADICAL WIPE: {err_msg}")
                # Complete wipe for next retry
                try: await self.context.close()
                except: pass
                try: await self.playwright.stop()
                except: pass
                self.playwright = None
                self.context = None
                self.controllers = {}
                raise RuntimeError(f"Browser-Crash erkannt. Bitte Request wiederholen (Self-Healing gestartet). Details: {err_msg}")
            raise e

tab_registry = TabRegistry()

async def browser_worker_loop():
    import json
    import time
    print('?? [Worker] Maus-Gott Loop gestartet...')
    while True:
        try:
            task: BrowserTask = await task_queue.get()
            request_id = task.request_id
            
            # Iron Fortress: Persistent picking
            log_task_persistent(task)
            
            print(f"[EVENT] {json.dumps({'event': 'REQUEST_PICKED', 'request_id': request_id, 'session_id': task.session_id, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})}")

            try:
                # 10 Minuten Limit (600s) fuer manuelle Interaktion und lange Scans
                async with asyncio.timeout(600.0):
                    provider = task.model_provider if hasattr(task, 'model_provider') and task.model_provider else 'AI_STUDIO'
                    controller = await tab_registry.get_or_create_controller(task.session_id, provider, request_id=request_id)
                    await controller.page.bring_to_front()
                    await controller.page.wait_for_timeout(500)

                    if task.action == 'generate':
                        # Ensure we are in a clean UI state every time
                        if hasattr(controller, 'ensure_fresh_chat'):
                            await controller.ensure_fresh_chat()
                            
                        if hasattr(controller, 'set_model') and task.model_name and provider == 'AI_STUDIO':
                            await controller.set_model(task.model_name)
                        
                        await controller.send_prompt(task.prompt)
                        response = await controller.wait_for_response()
                        
                        # Detect if response itself contains an error
                        if "fehler" in response.lower() or "timeout" in response.lower():
                             # If it's a fatal browser error returned as string (fallback), 
                             # we might still want to retry here, but usually it's caught by Exception.
                             err_type = "internal_error"
                             if "quota" in response.lower() or "limit" in response.lower():
                                 err_type = "quota_exceeded"
                             
                             error_data = {
                                 "status": "error",
                                 "type": err_type,
                                 "details": response
                             }
                             # Iron Fortress: Save Result before completing
                             save_result(request_id, error_data)
                             
                             print(f"[EVENT] {json.dumps({'event': 'TASK_COMPLETED', 'request_id': request_id, 'status': 'error', 'type': err_type, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})}")
                             if not task.future.done():
                                 task.future.set_result(json.dumps(error_data))
                        else:
                             # Success!
                             success_data = {
                                 "status": "success",
                                 "response": response,
                                 "request_id": request_id
                             }
                             # Iron Fortress: Save Result
                             save_result(request_id, success_data)
                             
                             print(f"[EVENT] {json.dumps({'event': 'TASK_COMPLETED', 'request_id': request_id, 'status': 'success', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})}")
                             if not task.future.done():
                                 task.future.set_result(json.dumps(success_data))
                    else:
                        raise ValueError(f'Unbekannte Aktion: {task.action}')

            except asyncio.TimeoutError:
                err_msg = f'Timeout (> 10 Min) fuer Session: {task.session_id}.'
                print(f"[EVENT] {json.dumps({'event': 'TASK_COMPLETED', 'request_id': request_id, 'status': 'error', 'type': 'timeout', 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})}")
                if not task.future.done():
                    task.future.set_result(json.dumps({
                        "status": "error",
                        "type": "timeout",
                        "details": err_msg
                    }))
            except Exception as e:
                err_msg = str(e)
                is_recoverable = "Protocol error" in err_msg or "closed" in err_msg or "Browser-Crash" in err_msg or "Target closed" in err_msg
                
                if is_recoverable and task.retry_count < 1:
                    print(f"[EVENT] {json.dumps({'event': 'TASK_RETRYING', 'request_id': request_id, 'retry_count': task.retry_count + 1, 'reason': err_msg, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})}")
                    task.retry_count += 1
                    # Fortress: 5s Cooldown to let OS clean up zombies/SingletonLock
                    await asyncio.sleep(5)
                    await task_queue.put(task)
                else:
                    status_val = "failed" if task.retry_count >= 1 else "error"
                    reason_val = "wipe_retry_exhausted" if task.retry_count >= 1 else "internal_error"
                    
                    err_data = {
                        "status": status_val,
                        "type": reason_val,
                        "reason": reason_val,
                        "attempts": task.retry_count + 1,
                        "details": err_msg
                    }
                    save_result(request_id, err_data)
                    
                    print(f"[EVENT] {json.dumps({'event': 'TASK_COMPLETED', 'request_id': request_id, 'status': status_val, 'type': reason_val, 'details': err_msg, 'timestamp': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime())})}")
                    if not task.future.done():
                        task.future.set_result(json.dumps(err_data))
            except BaseException as e:
                # Absolute last line of defense for hanging futures
                if not task.future.done():
                    task.future.set_result(json.dumps({"status": "failed", "type": "worker_crash", "details": str(e)}))
                raise e
            finally:
                # Iron Fortress: Cleanup persistent queue
                remove_task_persistent(request_id)
                
                print(f'Task fuer Session {task.session_id} beendet. Lock frei.')
                task_queue.task_done()
        except BaseException as loop_err:
            import traceback
            print(f"[Worker] Fatal Loop Error: {loop_err}")
            traceback.print_exc()
            await asyncio.sleep(1)

mcp = FastMCP('Browser-Hub-God-Container')

@mcp.tool()
async def debug_page(session_id: str) -> str:
    """Diagnose-Tool: Gibt URL + Selector-Counts der aktuellen Browser-Seite zurück."""
    try:
        if not tab_registry.context or not tab_registry.context.pages:
            return "Kein Browser-Context aktiv."
        page = tab_registry.context.pages[0]
        url = page.url

        selectors = [
            ".model-turn", "model-turn", "ms-text-chunk", "ms-chat-turn",
            ".message-content", "message-content", "[class*='model']",
            "section.chat-history", "chat-history", "ms-prompt-chunk",
            ".response-content", "mat-expansion-panel", "rich-text-editor",
            "p", "h1", "h2", "h3"
        ]

        results = [f"URL: {url}"]
        for sel in selectors:
            try:
                count = await page.locator(sel).count()
                results.append(f"  [{count:3d}] {sel}")
            except Exception as e:
                results.append(f"  [ERR] {sel}: {e}")

        # Custom element tags
        custom_tags = await page.evaluate("""() => {
            const tags = new Set();
            document.querySelectorAll('*').forEach(el => tags.add(el.tagName.toLowerCase()));
            return [...tags].filter(t => t.includes('-')).sort();
        }""")
        results.append(f"\nCustom Elements ({len(custom_tags)}):")
        results.extend([f"  <{t}>" for t in custom_tags[:40]])

        return "\n".join(results)
    except Exception as e:
        import traceback
        return f"debug_page error: {e}\n{traceback.format_exc()}"


@mcp.tool()
async def ask_gemini(session_id: str, prompt: str, model_name: str = 'Gemini 3.1 Pro Preview', request_id: str = "N/A") -> str:
    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        queue_pos = task_queue.qsize()

        task = BrowserTask(
            session_id=session_id, action='generate', request_id=request_id,
            prompt=prompt, model_name=model_name, model_provider='AI_STUDIO', future=future
        )
        await task_queue.put(task)
        return await future
    except Exception as e:
        import traceback
        print(f"[ask_gemini] Exception caught: {e}")
        traceback.print_exc()
        return f'Worker failed: {str(e)}'
    except BaseException as e:
        import traceback
        print(f"[ask_gemini] BaseException caught (TaskGroup crash prevent): {e}")
        traceback.print_exc()
        return f'Critical task failure: {str(e)}'

@mcp.tool()
async def ask_chatgpt(session_id: str, prompt: str, model_name: str = 'ChatGPT') -> str:
    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        queue_pos = task_queue.qsize()
        print(f'[MCP] Task fuer {session_id} (ChatGPT) auf pos {queue_pos}')

        task = BrowserTask(
            session_id=session_id, action='generate', prompt=prompt,
            model_name=model_name, model_provider='CHATGPT', future=future
        )
        await task_queue.put(task)
        return await future
    except Exception as e:
        return f'Worker failed: {str(e)}'
    except BaseException as e:
        return f'Critical task failure: {str(e)}'

@mcp.tool()
async def ask_claude(session_id: str, prompt: str, model_name: str = 'Claude') -> str:
    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        queue_pos = task_queue.qsize()
        print(f'[MCP] Task fuer {session_id} (Claude) auf pos {queue_pos}')

        task = BrowserTask(
            session_id=session_id, action='generate', prompt=prompt,
            model_name=model_name, model_provider='CLAUDE', future=future
        )
        await task_queue.put(task)
        return await future
    except Exception as e:
        return f'Worker failed: {str(e)}'
    except BaseException as e:
        return f'Critical task failure: {str(e)}'

@mcp.tool()
async def ask_deepseek(session_id: str, prompt: str, model_name: str = 'DeepSeek') -> str:
    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        queue_pos = task_queue.qsize()
        print(f'[MCP] Task fuer {session_id} (DeepSeek) auf pos {queue_pos}')

        task = BrowserTask(
            session_id=session_id, action='generate', prompt=prompt,
            model_name=model_name, model_provider='DEEPSEEK', future=future
        )
        await task_queue.put(task)
        return await future
    except Exception as e:
        return f'Worker failed: {str(e)}'
    except BaseException as e:
        return f'Critical task failure: {str(e)}'

@mcp.tool()
async def ask_perplexity(session_id: str, prompt: str, model_name: str = 'Perplexity') -> str:
    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        queue_pos = task_queue.qsize()
        print(f'[MCP] Task fuer {session_id} (Perplexity) auf pos {queue_pos}')

        task = BrowserTask(
            session_id=session_id, action='generate', prompt=prompt,
            model_name=model_name, model_provider='PERPLEXITY', future=future
        )
        await task_queue.put(task)
        return await future
    except Exception as e:
        return f'Worker failed: {str(e)}'
    except BaseException as e:
        return f'Critical task failure: {str(e)}'

app = FastAPI()

@app.on_event('startup')
async def startup_event():
    # Iron Fortress: Startup Resurrection (Idempotent Recovery)
    try:
        if os.path.exists(QUEUE_FILE):
            with open(QUEUE_FILE, 'r') as f: pending = json.load(f)
            count = 0
            for t in pending:
                # Idempotency: Skip if result already exists
                if os.path.exists(os.path.join(RESULTS_DIR, f"{t['request_id']}.json")):
                    continue
                
                new_task = BrowserTask(
                    session_id=t['session_id'],
                    action='generate', # Re-assume generate
                    request_id=t['request_id'],
                    prompt=t['prompt'],
                    model_name=t['model_name'],
                    model_provider=t['model_provider'],
                    retry_count=0, # Reset retries for fresh run
                    future=asyncio.Future() # Dummy future since caller is gone
                )
                await task_queue.put(new_task)
                count += 1
            if count > 0:
                print(f"[Fortress] 🏰 RESURRECTION: Recovered {count} tasks from persistent queue.")
    except Exception as e: print(f"[Fortress] Recovery error: {e}")
    
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
