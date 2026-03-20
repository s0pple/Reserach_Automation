"""
The Crucible – Core Workflow
Maschinenlesbarer State-Machine Workflow.
Entspricht dem Diagramm: Telegram → Local LLM → CLI → Cloud LLM (optional) → Telegram
"""

import asyncio
import json
import os
import time
import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, List, Dict, Any

from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# Ensure project root is in path
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Import AI Studio Client
try:
    from scripts.aistudio_client import AIStudioClient
except ImportError:
    from scripts.aistudio_client import AIStudioClient

# Logging Setup
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)
log = logging.getLogger("crucible")

# ─────────────────────────────────────────────
# CONFIG & GLOBALS
# ─────────────────────────────────────────────

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
DEFAULT_CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None

# Globals
bot_app = None
ai_client = None

# ─────────────────────────────────────────────
# STATES & DATA STRUCTURES
# ─────────────────────────────────────────────

class State(Enum):
    IDLE = "idle"
    PLANNING = "planning"
    CACHE_CHECK = "cache_check"
    FAST_PATH = "fast_path"
    CLOUD_LLM = "cloud_llm"
    EXECUTING = "executing"
    VERIFYING = "verifying"
    SAVING_WORKFLOW = "saving_workflow"
    DONE = "done"
    HITL = "hitl"
    FAILED = "failed"

@dataclass
class WorkflowStep:
    action: str
    target: str
    template_path: Optional[str] = None
    x: Optional[int] = None
    y: Optional[int] = None
    value: Optional[str] = None

@dataclass
class Session:
    goal: str
    chat_id: str
    steps: List[WorkflowStep] = field(default_factory=list)
    completed_steps: List[int] = field(default_factory=list)
    current_step_idx: int = 0
    retry_count: int = 0
    max_retries: int = 3
    cloud_calls: int = 0
    max_cloud_calls: int = 10
    state: State = State.IDLE
    last_error: Optional[str] = None
    result: Optional[str] = None

# ─────────────────────────────────────────────
# TOOL-STUBS & IMPLEMENTATIONS
# ─────────────────────────────────────────────

async def local_llm_plan(goal: str) -> List[WorkflowStep]:
    log.info(f"[LOCAL LLM] Plane fuer Ziel: {goal}")
    return []

def load_cached_workflow(goal: str) -> Optional[List[WorkflowStep]]:
    path = "workflows/workflow_cache.json"
    if not os.path.exists(path): return None
    try:
        with open(path, "r") as f:
            cache = json.load(f)
        if goal in cache:
            log.info(f"[CACHE] Hit fuer Ziel: {goal}")
            return [WorkflowStep(**s) for s in cache[goal]]
    except Exception as e:
        log.warning(f"[CACHE] Fehler beim Laden: {e}")
    return None

def save_workflow(goal: str, steps: List[WorkflowStep]) -> None:
    os.makedirs("workflows", exist_ok=True)
    path = "workflows/workflow_cache.json"
    cache = {}
    if os.path.exists(path):
        try:
            with open(path, "r") as f: cache = json.load(f)
        except Exception: pass
    cache[goal] = [s.__dict__ for s in steps]
    with open(path, "w") as f: json.dump(cache, f, indent=2)
    log.info(f"[CACHE] Workflow gespeichert fuer: {goal}")

async def fast_path_execute(step: WorkflowStep) -> bool:
    log.info(f"[FAST PATH] {step.action} -> {step.target}")
    if step.x is not None and step.y is not None: return True
    return False

async def execution_verify(step: WorkflowStep) -> bool:
    log.info(f"[VERIFY] Pruefe Ergebnis von: {step.target}")
    return True

async def ensure_ai_client():
    global ai_client
    if ai_client is None:
        ai_client = AIStudioClient()
        await ai_client.start(headless=False)

async def ask_cloud_llm(goal: str, screenshot_path: str, error_ctx: str) -> Optional[WorkflowStep]:
    log.info(f"[CLOUD LLM] Frage AI Studio (Fehler: {error_ctx})")
    
    try:
        await ensure_ai_client()
    except Exception as e:
        log.error(f"[CLOUD LLM] ensure_ai_client failed: {e}")
        return None

    page = ai_client.page
    if not page:
        log.error("[CLOUD LLM] ai_client.page is None! Browser failed to start or context lost.")
        return None
        
    try:
        # Construct prompt
        prompt = f"""
I am an automation agent.
MY GOAL: {goal}
CURRENT ERROR/CONTEXT: {error_ctx}

Analyze the attached screenshot. What is the single next step I must take?
Respond in this format:
ACTION: [click | type | wait | done]
TARGET: [description of element or text to type]
REASONING: [brief explanation]
"""
        # 1. Upload Screenshot
        log.info(f"[CLOUD LLM] Uploading screenshot: {screenshot_path}")
        await page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        
        upload_btn = page.locator('button[aria-label="Insert images, videos, audio, or files"], button .mat-icon:has-text("add_circle")').first
        if await upload_btn.count() > 0:
            await upload_btn.click()
            await asyncio.sleep(1)
            
            file_input = page.locator('input[type="file"]').first
            await file_input.set_input_files(screenshot_path)
            await asyncio.sleep(2)
            log.info("[CLOUD LLM] Upload successful.")
        else:
            log.warning("[CLOUD LLM] Upload button not found! Attempting prompt anyway.")
        
        # 2. Send Prompt
        log.info("[CLOUD LLM] Calling ai_client.ask()...")
        response_text = await ai_client.ask(prompt)
        log.info(f"[CLOUD LLM] Received response: {response_text[:100]}...")
        
        # 3. Parse Response (Simple Heuristic)
        lines = response_text.split('\n')
        action = "wait"
        target = "analysis"
        
        for line in lines:
            if line.upper().startswith("ACTION:"):
                action = line.split(":", 1)[1].strip().lower()
            if line.upper().startswith("TARGET:"):
                target = line.split(":", 1)[1].strip()
                
        return WorkflowStep(action=action, target=target)
        
    except Exception as e:
        log.error(f"[CLOUD LLM] Error in ask_cloud_llm: {e}", exc_info=True)
        return None

async def take_screenshot(path: str = "temp/current.png") -> str:
    os.makedirs("temp", exist_ok=True)
    await ensure_ai_client()
    if ai_client and ai_client.page:
        await ai_client.page.screenshot(path=path)
        return path
    return ""

async def send_telegram(chat_id: str, text: str, screenshot_path: Optional[str] = None, buttons: Optional[List[Any]] = None) -> None:
    if not bot_app: return
    log.info(f"[TELEGRAM -> {chat_id}] {text}")
    markup = None
    if buttons:
        keyboard = []
        for label, data in buttons:
            keyboard.append([InlineKeyboardButton(label, callback_data=data)])
        markup = InlineKeyboardMarkup(keyboard)

    try:
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, "rb") as f:
                await bot_app.bot.send_photo(chat_id=chat_id, photo=f, caption=text[:1024], reply_markup=markup)
        else:
            await bot_app.bot.send_message(chat_id=chat_id, text=text, reply_markup=markup)
    except Exception as e:
        log.error(f"[TELEGRAM] Failed to send: {e}")

_hitl_event = asyncio.Event()
_hitl_decision: Optional[str] = None

async def wait_for_human(session: Session) -> str:
    global _hitl_decision
    _hitl_decision = None
    _hitl_event.clear()
    screenshot = await take_screenshot()
    await send_telegram(session.chat_id, f"🆘 **HITL**\nHilfe bei: `{session.goal}`\nFehler: {session.last_error}", screenshot, [("Skip", "skip"), ("Magic Click", "magic_click"), ("Abort", "abort")])
    log.info("[HITL] Warte auf Telegram-Input...")
    await _hitl_event.wait()
    return _hitl_decision or "skip"

def hitl_resolve(decision: str) -> None:
    global _hitl_decision
    _hitl_decision = decision
    _hitl_event.set()

async def run_workflow(goal: str, chat_id: str) -> str:
    session = Session(goal=goal, chat_id=chat_id)
    await send_telegram(chat_id, f"🚀 Starte Workflow: `{goal}`")

    while session.state not in (State.DONE, State.FAILED):
        if session.state == State.IDLE:
            session.state = State.PLANNING
            session.steps = await local_llm_plan(goal)
            session.state = State.CACHE_CHECK
        elif session.state == State.CACHE_CHECK:
            cached = load_cached_workflow(goal)
            if cached:
                session.steps = cached
                session.state = State.FAST_PATH
            else:
                session.state = State.CLOUD_LLM
        elif session.state == State.FAST_PATH:
            if session.current_step_idx >= len(session.steps):
                session.state = State.DONE
                continue
            step = session.steps[session.current_step_idx]
            success = await fast_path_execute(step)
            if success: session.state = State.VERIFYING
            else:
                session.retry_count += 1
                if session.retry_count >= session.max_retries:
                    session.last_error = f"Template nicht gefunden: {step.template_path}"
                    session.state = State.HITL
                else: session.state = State.CLOUD_LLM
        elif session.state == State.CLOUD_LLM:
            if session.cloud_calls >= session.max_cloud_calls:
                session.last_error = "Max Cloud Calls"
                session.state = State.HITL
                continue
            screenshot = await take_screenshot()
            error_ctx = session.last_error or "Kein Cache"
            new_step = await ask_cloud_llm(goal, screenshot, error_ctx)
            session.cloud_calls += 1
            if new_step:
                if session.current_step_idx < len(session.steps):
                     session.steps.insert(session.current_step_idx, new_step)
                else: session.steps.append(new_step)
                session.state = State.FAST_PATH
            else:
                session.retry_count += 1
                if session.retry_count >= session.max_retries:
                    session.last_error = "Cloud LLM fail"
                    session.state = State.HITL
        elif session.state == State.VERIFYING:
            step = session.steps[session.current_step_idx]
            ok = await execution_verify(step)
            if ok:
                session.completed_steps.append(session.current_step_idx)
                session.current_step_idx += 1
                session.retry_count = 0
                session.state = State.SAVING_WORKFLOW if session.current_step_idx >= len(session.steps) else State.FAST_PATH
            else:
                session.retry_count += 1
                session.last_error = f"Verifikation fehlgeschlagen"
                session.state = State.CLOUD_LLM if session.retry_count < session.max_retries else State.HITL
        elif session.state == State.SAVING_WORKFLOW:
            save_workflow(goal, session.steps)
            session.state = State.DONE
        elif session.state == State.HITL:
            decision = await wait_for_human(session)
            session.retry_count = 0
            if decision == "skip":
                session.current_step_idx += 1
                session.state = State.FAST_PATH
            elif decision == "magic_click":
                session.state = State.FAST_PATH
            else: session.state = State.FAILED

    msg = f"Fertig: {goal}" if session.state == State.DONE else f"Abbruch: {session.last_error}"
    await send_telegram(chat_id, ("✅ " if session.state == State.DONE else "❌ ") + msg)
    return msg

# ─────────────────────────────────────────────
# HANDLERS & MAIN
# ─────────────────────────────────────────────

async def telegram_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text: return
    user_id = update.effective_user.id
    chat_id = update.effective_chat.id
    text = update.message.text
    
    log.info(f"[DEBUG] Msg from {user_id}: {text}")

    if ALLOWED_IDS and user_id not in ALLOWED_IDS:
        log.warning(f"[DENIED] User {user_id}")
        return

    # Trigger Workflow in background
    asyncio.create_task(run_workflow(text, chat_id))

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    hitl_resolve(query.data)
    await query.edit_message_caption(caption=f"Input: {query.data}")

async def main():
    global bot_app
    
    if not TELEGRAM_TOKEN:
        log.error("No TELEGRAM_TOKEN")
        return

    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, telegram_handler))
    bot_app.add_handler(CallbackQueryHandler(callback_handler))
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    
    log.info("🚀 Crucible Loop Online! Warte auf Befehle...")
    
    # Init AI Client (non-blocking)
    asyncio.create_task(ensure_ai_client())
    
    try:
        while True: 
            await asyncio.sleep(3600)
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
