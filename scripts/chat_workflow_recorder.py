import asyncio
import os
import sys
import logging
import json
import time
import pyperclip
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image

sys.path.append("/app")
from src.modules.browser.magic_link import get_user_click_via_magic_link

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ChatRecorder")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

# State
browser_page = None
bot_app = None
workflow_steps = []
current_workflow_name = "default_workflow"

# --- Helper: Save Template Crop ---
def save_crop(image_path, x, y, label):
    os.makedirs("temp/workflows", exist_ok=True)
    with Image.open(image_path) as img:
        left, top = max(0, x - 50), max(0, y - 50)
        right, bottom = min(img.width, x + 50), min(img.height, y + 50)
        crop = img.crop((left, top, right, bottom))
        path = f"temp/workflows/tpl_{current_workflow_name}_{len(workflow_steps)}.png"
        crop.save(path)
        return path

async def init_browser():
    global browser_page
    p = await async_playwright().start()
    args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
    context = await p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_PATH, headless=False, args=args, viewport={"width": 1280, "height": 800}
    )
    browser_page = context.pages[0] if context.pages else await context.new_page()

async def send_status(text, include_magic_btn=False):
    markup = None
    if include_magic_btn:
        markup = InlineKeyboardMarkup([[InlineKeyboardButton("✨ Magic Klick (Maus)", callback_data='magic_click')]])
    
    # Screenshot mitsenden für Kontext
    path = "temp/chat_view.png"
    await browser_page.screenshot(path=path)
    with open(path, "rb") as f:
        await bot_app.bot.send_photo(chat_id=CHAT_ID, photo=f, caption=text, reply_markup=markup, parse_mode='Markdown')

# --- Handlers ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global workflow_steps, current_workflow_name
    if update.effective_user.id not in ALLOWED_IDS: return
    
    text = update.message.text.strip()
    cmd_parts = text.split(" ", 1)
    cmd = cmd_parts[0].lower()
    arg = cmd_parts[1] if len(cmd_parts) > 1 else ""

    if cmd == "open":
        await update.message.reply_text("🔄 Öffne AI Studio...")
        await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await asyncio.sleep(5)
        await send_status("✅ Bereit. Nutze `tippe ...`, `enter`, `copy`, `warte ...` oder klicke den Button für die Maus.", include_magic_btn=True)

    elif cmd in ["tippe", "type"]:
        await browser_page.keyboard.type(arg)
        workflow_steps.append({"type": "type", "text": arg})
        await send_status(f"⌨️ Getippt: `{arg}`", include_magic_btn=True)

    elif cmd == "enter":
        await browser_page.keyboard.press("Enter")
        workflow_steps.append({"type": "press", "key": "Enter"})
        await send_status("⏎ Enter gedrückt.", include_magic_btn=True)
        
    elif cmd == "ctrl+enter":
        await browser_page.keyboard.press("Control+Enter")
        workflow_steps.append({"type": "hotkey", "keys": ["Control", "Enter"]})
        await send_status("🚀 Prompt gesendet (Ctrl+Enter).", include_magic_btn=True)

    elif cmd in ["warte", "wait"]:
        sec = int(arg) if arg.isdigit() else 5
        await update.message.reply_text(f"⏳ Warte {sec} Sekunden...")
        await asyncio.sleep(sec)
        workflow_steps.append({"type": "wait", "seconds": sec})
        await send_status("✅ Weiter geht's.", include_magic_btn=True)

    elif cmd == "copy":
        # Simuliert Ctrl+A, Ctrl+C und liest Clipboard
        # Fokus setzen (klicken wir mal blind in die Mitte oder nutzen letzten Klick)
        # Besser: Wir verlassen uns drauf, dass der User vorher geklickt hat.
        await browser_page.keyboard.press("Control+a")
        await asyncio.sleep(0.5)
        await browser_page.keyboard.press("Control+c")
        await asyncio.sleep(0.5)
        
        # Clipboard auslesen via Playwright Evaluation
        content = await browser_page.evaluate("navigator.clipboard.readText()")
        
        workflow_steps.append({"type": "copy"})
        await update.message.reply_text(f"📋 **Kopierter Inhalt:**\n\n```text\n{content[:2000]}\n```", parse_mode='Markdown')
        await send_status("✅ Copy-Action aufgezeichnet.", include_magic_btn=True)

    elif cmd == "frage":
        # Der AI-Loop Integration!
        await update.message.reply_text("🧠 Frage AI Studio um Rat (lädt Screenshot hoch)...")
        
        # 1. Screenshot speichern
        path = "temp/ai_query.png"
        await browser_page.screenshot(path=path)
        
        try:
            # 2. Upload Button finden & klicken (wir nehmen an, wir sind im AI Studio)
            await browser_page.keyboard.press("Escape") # Close overlays
            await browser_page.locator('button[aria-label="Insert images, videos, audio, or files"]').click()
            await asyncio.sleep(1)
            await browser_page.locator('input[type="file"]').set_input_files(path)
            await asyncio.sleep(2)
            
            # 3. Frage eintippen
            textarea = browser_page.locator('textarea, div[contenteditable="true"]').last
            await textarea.fill(f"Ich baue eine Automatisierung. Schau dir den Screenshot an. {arg}")
            await browser_page.keyboard.press("Control+Enter")
            
            await update.message.reply_text("⏳ Warte auf Antwort...")
            await asyncio.sleep(15) # Simples Warten für jetzt
            
            # 4. Antwort lesen
            response = await browser_page.evaluate('''() => {
                const els = document.querySelectorAll('.model-response-text');
                return els.length ? els[els.length - 1].innerText : "Keine Antwort gefunden";
            }''')
            
            await update.message.reply_text(f"🤖 **AI Studio sagt:**\n{response}")
            
        except Exception as e:
            await update.message.reply_text(f"💥 Fehler beim Fragen: {e}")

    elif cmd == "save":
        name = arg or "workflow"
        with open(f"temp/workflows/{name}.json", "w") as f:
            json.dump(workflow_steps, f, indent=4)
        await update.message.reply_text(f"💾 Workflow `{name}.json` gespeichert! ({len(workflow_steps)} Schritte)")
        
    elif cmd == "reset":
        workflow_steps = []
        await update.message.reply_text("🗑️ Workflow-Speicher geleert.")

    else:
        await update.message.reply_text("❓ Unbekannt. Nutze: `tippe`, `enter`, `copy`, `warte`, `frage`, `save` oder den Button.")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global workflow_steps
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    if query.data == 'magic_click':
        await query.edit_message_caption(caption="🪄 Generiere Link...")
        path = "temp/click_view.png"
        await browser_page.screenshot(path=path)
        
        coords = await get_user_click_via_magic_link(path, bot_app, CHAT_ID, "klicken")
        if coords:
            x, y = coords
            # Template vor dem Klick speichern
            clean_path = "temp/clean_click.png"
            await browser_page.screenshot(path=clean_path)
            tpl_path = save_crop(clean_path, x, y, f"step_{len(workflow_steps)}")
            
            # Klick ausführen
            await browser_page.mouse.click(x, y)
            
            workflow_steps.append({
                "type": "click",
                "x": x, "y": y,
                "template": tpl_path
            })
            await send_status(f"🎯 Klick bei {x},{y} registriert.", include_magic_btn=True)
        else:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Klick abgebrochen.")

async def main():
    global bot_app
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    await init_browser()
    await bot_app.bot.send_message(chat_id=CHAT_ID, text="🎙️ **Chat Recorder Online**\nSchreibe `open`, um zu starten.")
    
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