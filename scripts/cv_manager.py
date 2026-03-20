import asyncio
import os
import sys
import logging
import json
import time
import cv2
import numpy as np
import mss
import pyautogui
import pyperclip
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes

sys.path.append("/app")
from src.modules.browser.magic_link import get_user_click_via_magic_link

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("CV_Manager")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

# --- Globals ---
browser_page = None
bot_app = None
current_mode = "idle" # 'record', 'replay', 'idle'
current_workflow_name = ""
recorded_steps = []

# --- Helper: Browser Init ---
async def init_browser():
    global browser_page
    p = await async_playwright().start()
    args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
    context = await p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_PATH, headless=False, args=args, viewport={"width": 1280, "height": 800}
    )
    browser_page = context.pages[0] if context.pages else await context.new_page()
    await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
    await asyncio.sleep(5)

# --- Human Simulation Layer ---
def take_screenshot_cv():
    with mss.mss() as sct:
        monitor = sct.monitors[1]
        screenshot = sct.grab(monitor)
        return cv2.cvtColor(np.frombuffer(screenshot.bgra, dtype=np.uint8).reshape(screenshot.height, screenshot.width, 4), cv2.COLOR_BGRA2BGR)

def screens_differ(img1, img2, threshold=0.01):
    """Vergleicht zwei Bilder. Gibt True zurück, wenn sie sich signifikant unterscheiden."""
    diff = cv2.absdiff(img1, img2)
    gray = cv2.cvtColor(diff, cv2.COLOR_BGR2GRAY)
    _, thresh = cv2.threshold(gray, 30, 255, cv2.THRESH_BINARY)
    non_zero_count = np.count_nonzero(thresh)
    total_pixels = img1.shape[0] * img1.shape[1]
    return (non_zero_count / total_pixels) > threshold

async def action_and_verify(action_coro, timeout=10):
    """Führt Aktion aus und wartet auf eine visuelle Änderung am Bildschirm (Human Simulation)."""
    screen_before = take_screenshot_cv()
    
    await action_coro() # Execute the click/type
    
    start = time.time()
    while time.time() - start < timeout:
        await asyncio.sleep(0.5)
        screen_after = take_screenshot_cv()
        if screens_differ(screen_before, screen_after):
            logger.info("Visuelle Änderung erkannt!")
            return True
    logger.warning("Keine visuelle Änderung nach Aktion erkannt.")
    return False

# --- Telegram UI & Routing ---
async def send_dashboard(text=""):
    path = "temp/dashboard.png"
    await browser_page.screenshot(path=path)
    
    if current_mode == "idle":
        buttons = [
            [InlineKeyboardButton("🔴 Record: AI Studio Prompting", callback_data='rec_aistudio')],
            [InlineKeyboardButton("▶️ Replay: AI Studio Prompting", callback_data='rep_aistudio')],
        ]
        msg = text or "🎛️ **CV-Bot Manager**\nWähle einen Modus:"
    elif current_mode == "record":
        buttons = [
            [InlineKeyboardButton("✨ Magic Klick aufzeichnen", callback_data='magic_click')],
            [InlineKeyboardButton("⌨️ Tastatur-Eingabe aufzeichnen", callback_data='record_type')],
            [InlineKeyboardButton("💾 Record Beenden & Speichern", callback_data='save_record')]
        ]
        msg = text or f"🔴 **Recording:** `{current_workflow_name}`\nSchritt {len(recorded_steps)+1}. Was willst du tun?"
    
    markup = InlineKeyboardMarkup(buttons)
    with open(path, "rb") as f:
        await bot_app.bot.send_photo(chat_id=CHAT_ID, photo=f, caption=msg, reply_markup=markup, parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_mode, current_workflow_name, recorded_steps
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    d = query.data
    
    if d == 'rec_aistudio':
        current_mode = "record"
        current_workflow_name = "aistudio_workflow.json"
        recorded_steps = []
        os.makedirs("temp/workflows", exist_ok=True)
        await query.edit_message_caption(caption="🔴 Starte Recording...")
        await send_dashboard()
        
    elif d == 'magic_click':
        await query.edit_message_caption(caption="🪄 Generiere Magic Link zum Klicken...")
        path = "temp/magic_view.png"
        await browser_page.screenshot(path=path)
        
        coords = await get_user_click_via_magic_link(path, bot_app, CHAT_ID, "klicken")
        if coords:
            x, y = coords
            # Template speichern
            img = take_screenshot_cv()
            left, top = max(0, x - 50), max(0, y - 50)
            right, bottom = min(img.shape[1], x + 50), min(img.shape[0], y + 50)
            crop = img[top:bottom, left:right]
            
            crop_path = f"temp/workflows/tpl_{current_workflow_name}_{len(recorded_steps)}.png"
            cv2.imwrite(crop_path, crop)
            
            # Aktion ausführen & verifizieren
            async def do_click():
                pyautogui.click(x, y)
                
            success = await action_and_verify(do_click)
            
            recorded_steps.append({
                "type": "click",
                "x": x, "y": y,
                "template": crop_path
            })
            
            await send_dashboard(f"✅ Klick gespeichert. Visuelle Änderung: {'Ja' if success else 'Nein (Timeout)'}")
        else:
            await send_dashboard("❌ Abbruch.")
            
    elif d == 'record_type':
        # Erwartet, dass der User als nächstes Text im Chat schreibt.
        # Für diesen POC machen wir ein hartcodiertes Beispiel (Ctrl+A, Ctrl+C für Copy)
        await query.edit_message_caption(caption="⌨️ Simuliere 'Markieren & Kopieren' (Ctrl+A, Ctrl+C)...")
        
        async def do_type():
            pyautogui.hotkey('ctrl', 'a')
            await asyncio.sleep(0.2)
            pyautogui.hotkey('ctrl', 'c')
            
        await action_and_verify(do_type, timeout=3)
        
        recorded_steps.append({
            "type": "hotkey",
            "keys": ["ctrl", "a", "ctrl", "c"]
        })
        await send_dashboard("✅ Tastatur-Aktion gespeichert.")
        
    elif d == 'save_record':
        with open(f"temp/workflows/{current_workflow_name}", "w") as f:
            json.dump(recorded_steps, f, indent=4)
        current_mode = "idle"
        await send_dashboard(f"💾 Workflow `{current_workflow_name}` gespeichert!")
        
    elif d == 'rep_aistudio':
        current_mode = "idle"
        wf_path = "temp/workflows/aistudio_workflow.json"
        if not os.path.exists(wf_path):
            await send_dashboard("❌ Kein Workflow gefunden! Bitte zuerst aufzeichnen.")
            return
            
        await query.edit_message_caption(caption="▶️ Führe Workflow aus...")
        
        with open(wf_path, "r") as f:
            steps = json.load(f)
            
        for i, step in enumerate(steps):
            await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"⚙️ Führe Schritt {i+1} aus: `{step['type']}`")
            
            if step['type'] == 'click':
                tpl = cv2.imread(step['template'])
                screen = take_screenshot_cv()
                res = cv2.matchTemplate(screen, tpl, cv2.TM_CCOEFF_NORMED)
                _, max_val, _, max_loc = cv2.minMaxLoc(res)
                
                if max_val > 0.8:
                    x = max_loc[0] + tpl.shape[1] // 2
                    y = max_loc[1] + tpl.shape[0] // 2
                    
                    async def do_click(): pyautogui.click(x, y)
                    success = await action_and_verify(do_click)
                    await asyncio.sleep(1)
                else:
                    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"❌ Template nicht gefunden (Conf: {max_val})")
                    break
                    
            elif step['type'] == 'hotkey':
                async def do_keys():
                    if "a" in step['keys']: # quick hack for the copy
                        pyautogui.hotkey('ctrl', 'a')
                        await asyncio.sleep(0.2)
                        pyautogui.hotkey('ctrl', 'c')
                await action_and_verify(do_keys, timeout=2)
                
                # Check clipboard
                copied = pyperclip.paste()
                await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"📋 **In Zwischenablage gefunden:**\n\n`{copied[:500]}...`")

        await send_dashboard("🏁 Replay beendet.")

async def main():
    global bot_app
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    await init_browser()
    await send_dashboard()
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    try:
        while True: await asyncio.sleep(3600)
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())