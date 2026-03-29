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

@dataclass
class BrowserTask:
    session_id: str
    action: str
    prompt: Optional[str] = None
    model_name: Optional[str] = None
    model_provider: Optional[str] = 'AI_STUDIO'  # Differentiates which controller to use
    system_instruction: Optional[str] = None
    future: asyncio.Future = None

task_queue: asyncio.Queue = asyncio.Queue()

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


    async def get_or_create_controller(self, session_id: str, provider: str = 'AI_STUDIO') -> Any:
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

        await self._ensure_single_tab()

        if session_id in self.controllers:
            return self.controllers[session_id]

        if len(self.controllers) >= self.max_tabs:
            print(f'[TabRegistry] RAM-Schutz: Entferne alte Controller (aktuell {len(self.controllers)})')
            for old_session, old_controller in list(self.controllers.items()):
                try:
                    await old_controller.page.close()
                except Exception as e:
                    print(f"[TabRegistry] Fehler beim Schliessen alter Seite: {e}")
                self.controllers.pop(old_session, None)

        # Falls mehr als 1 Page im Context ist, bereinigen
        await self._ensure_single_tab()

        if len(self.controllers) >= self.max_tabs:
            raise RuntimeError(f'RAM-Schutz aktiv. Maximum {self.max_tabs} erreicht.')

        if len(self.controllers) == 0 and len(self.context.pages) > 0:
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
            controller = AIStudioController(page)
            
        print(f'[TabRegistry] Initialisiere Session in TAB fuer {session_id} mit {provider}')
        await controller.init_session()
        self.controllers[session_id] = controller
        return controller

tab_registry = TabRegistry()

async def browser_worker_loop():
    print('?? [Worker] Maus-Gott Loop gestartet...')
    while True:
        try:
            task: BrowserTask = await task_queue.get()
            print(f'[Worker] Task gepickt: Session {task.session_id} | {task.action}')

            try:
                # 10 Minuten Limit (600s) fuer manuelle Interaktion und lange Scans
                async with asyncio.timeout(600.0):
                    provider = task.model_provider if hasattr(task, 'model_provider') and task.model_provider else 'AI_STUDIO'
                    controller = await tab_registry.get_or_create_controller(task.session_id, provider)
                    await controller.page.bring_to_front()
                    await controller.page.wait_for_timeout(500)

                    if task.action == 'generate':
                        if hasattr(controller, 'set_model') and task.model_name and provider == 'AI_STUDIO':
                            await controller.set_model(task.model_name)
                        
                        await controller.send_prompt(task.prompt)
                        response = await controller.wait_for_response()
                        if not task.future.done():
                            task.future.set_result(response)
                    else:
                        raise ValueError(f'Unbekannte Aktion: {task.action}')

            except asyncio.TimeoutError:
                err_msg = f'Timeout (> 10 Min) fuer Session: {task.session_id}.'
                print(err_msg)
                if not task.future.done():
                    task.future.set_exception(Exception(err_msg))
            except Exception as e:
                print(f'Fehler im Task: {e}')
                if not task.future.done():
                    task.future.set_exception(e)
            except BaseException as e:
                import traceback
                print(f'[Worker] Task BaseException caught: {e}')
                traceback.print_exc()
                if not task.future.done():
                    task.future.set_exception(Exception(f"Worker BaseException: {str(e)}"))
            finally:
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
async def ask_gemini(session_id: str, prompt: str, model_name: str = 'Gemini 3.1 Pro Preview') -> str:
    try:
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        queue_pos = task_queue.qsize()
        print(f'[MCP] Task fuer {session_id} auf pos {queue_pos}')

        task = BrowserTask(
            session_id=session_id, action='generate', prompt=prompt,
            model_name=model_name, model_provider='AI_STUDIO', future=future
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
