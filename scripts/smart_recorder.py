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
from google import genai
from google.genai import types
from pydantic import BaseModel, Field

sys.path.append("/app")
from src.modules.browser.magic_link import get_user_click_via_magic_link

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartRecorder")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# State
browser_page = None
bot_app = None
workflow_steps = []
current_workflow_name = "default_workflow"
pending_suggestion = None # Speichert den aktuellen KI-Vorschlag

# --- Data Models ---
class StepSuggestion(BaseModel):
    reasoning: str = Field(description="Warum wir das tun.")
    action_type: str = Field(description="'click', 'type', 'wait', 'hotkey', 'done', 'unknown'")
    target_text: str = Field(default="", description="Text des Elements zum Klicken.")
    input_text: str = Field(default="", description="Text zum Tippen.")
    key_combo: str = Field(default="", description="Tastenkombination (z.B. 'Control+Enter').")

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

async def get_ai_suggestion(user_text):
    path = "temp/ai_view.png"
    await browser_page.screenshot(path=path)
    
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    prompt = f"""
Du bist ein UI-Automatisierungs-Assistent. Der User will: "{user_text}".
Analysiere den Screenshot. Was ist der EINZIGE nächste logische Schritt?
- Wenn geklickt werden muss: Gib action_type='click' und den sichtbaren Text in 'target_text'.
- Wenn getippt werden muss: Gib action_type='type' und den Text in 'input_text'.
- Wenn eine Taste gedrückt werden muss (z.B. Enter, Ctrl+Enter): action_type='hotkey'.
- Wenn gewartet werden muss (z.B. Ladespinner): action_type='wait'.
- Wenn das Ziel erreicht scheint: action_type='done'.
Halte dich kurz.
"""
    with Image.open(path) as img:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=StepSuggestion,
                temperature=0.0
            ),
        )
    return StepSuggestion.model_validate_json(response.text)

async def execute_suggestion(suggestion: StepSuggestion):
    global workflow_steps
    
    if suggestion.action_type == 'click':
        # Versuche Element zu finden
        try:
            loc = browser_page.locator(f'text="{suggestion.target_text}"').first
            box = await loc.bounding_box()
            if box:
                # Screenshot für Template VOR dem Klick
                clean_path = "temp/clean_pre_click.png"
                await browser_page.screenshot(path=clean_path)
                
                x = int(box['x'] + box['width'] / 2)
                y = int(box['y'] + box['height'] / 2)
                
                tpl_path = save_crop(clean_path, x, y, f"step_{len(workflow_steps)}")
                await loc.click(timeout=3000)
                
                workflow_steps.append({"type": "click", "x": x, "y": y, "template": tpl_path})
                return f"✅ Klick auf '{suggestion.target_text}' ausgeführt & gespeichert."
            else:
                return "❌ Element nicht gefunden (Bounding Box leer)."
        except Exception as e:
            return f"❌ Fehler beim Klicken: {e}"

    elif suggestion.action_type == 'type':
        await browser_page.keyboard.type(suggestion.input_text)
        workflow_steps.append({"type": "type", "text": suggestion.input_text})
        return f"✅ Text '{suggestion.input_text}' getippt."

    elif suggestion.action_type == 'hotkey':
        keys = suggestion.key_combo.replace("+", "+") # Normalize
        await browser_page.keyboard.press(keys)
        workflow_steps.append({"type": "hotkey", "keys": keys})
        return f"✅ Tasten '{keys}' gedrückt."
        
    elif suggestion.action_type == 'wait':
        await asyncio.sleep(5)
        workflow_steps.append({"type": "wait", "seconds": 5})
        return "✅ 5 Sekunden gewartet."

    return "⚠️ Aktion nicht ausführbar."

async def send_status(text, buttons=None):
    path = "temp/status_view.png"
    await browser_page.screenshot(path=path)
    markup = InlineKeyboardMarkup(buttons) if buttons else None
    with open(path, "rb") as f:
        await bot_app.bot.send_photo(chat_id=CHAT_ID, photo=f, caption=text, reply_markup=markup, parse_mode='Markdown')

# --- Handlers ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global workflow_steps, pending_suggestion
    if update.effective_user.id not in ALLOWED_IDS: return
    
    text = update.message.text.strip()
    low_text = text.lower()

    # 1. Direkte Befehle (Manuelle Kontrolle)
    if low_text == "open":
        await update.message.reply_text("🔄 Öffne AI Studio...")
        await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await asyncio.sleep(5)
        await send_status("✅ Bereit. Sag mir was ich tun soll!", [[InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click')]])
        return
        
    elif low_text == "save":
        with open(f"temp/workflows/chat_workflow.json", "w") as f:
            json.dump(workflow_steps, f, indent=4)
        await update.message.reply_text(f"💾 Workflow gespeichert ({len(workflow_steps)} Schritte).")
        return

    # 2. Smart Mode (KI-Analyse)
    await update.message.reply_text(f"🤔 Denke nach über: '{text}'...")
    
    try:
        suggestion = await get_ai_suggestion(text)
        pending_suggestion = suggestion
        
        buttons = [
            [InlineKeyboardButton("🚀 Ausführen & Speichern", callback_data='exec_suggestion')],
            [InlineKeyboardButton("✨ Magic Klick (Manuell)", callback_data='magic_click')],
            [InlineKeyboardButton("🛑 Abbrechen", callback_data='abort')]
        ]
        
        caption = f"🤖 **Vorschlag:** `{suggestion.action_type}`\n"
        if suggestion.target_text: caption += f"Target: `{suggestion.target_text}`\n"
        if suggestion.input_text: caption += f"Input: `{suggestion.input_text}`\n"
        caption += f"\n💡 *{suggestion.reasoning}*"
        
        await send_status(caption, buttons)
        
    except Exception as e:
        await update.message.reply_text(f"💥 KI-Fehler: {e}")

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global workflow_steps, pending_suggestion
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    if query.data == 'exec_suggestion' and pending_suggestion:
        await query.edit_message_caption(caption=f"⚙️ Führe aus: {pending_suggestion.action_type}...")
        result = await execute_suggestion(pending_suggestion)
        
        # Nächste Optionen
        buttons = [[InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click')]]
        await send_status(f"{result}\nWas als nächstes?", buttons)
        pending_suggestion = None
        
    elif query.data == 'magic_click':
        await query.edit_message_caption(caption="🪄 Generiere Magic Link...")
        path = "temp/click_view.png"
        await browser_page.screenshot(path=path)
        
        coords = await get_user_click_via_magic_link(path, bot_app, CHAT_ID, "klicken")
        if coords:
            x, y = coords
            clean_path = "temp/clean_click.png"
            await browser_page.screenshot(path=clean_path)
            tpl_path = save_crop(clean_path, x, y, f"step_{len(workflow_steps)}")
            
            await browser_page.mouse.click(x, y)
            workflow_steps.append({"type": "click", "x": x, "y": y, "template": tpl_path})
            await send_status(f"🎯 Manuell geklickt bei {x},{y}.", [[InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click')]])
        else:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Klick abgebrochen.")

async def main():
    global bot_app
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    await init_browser()
    await bot_app.bot.send_message(chat_id=CHAT_ID, text="🧠 **Smart Recorder Online**\nIch verstehe natürliche Sprache! Schreib einfach dein Ziel.")
    
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