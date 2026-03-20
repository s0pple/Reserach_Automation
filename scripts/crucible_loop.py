import asyncio
import os
import sys
import logging
import json
import re
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from PIL import Image

sys.path.append("/app")
from src.modules.browser.magic_link import get_user_click_via_magic_link
from src.modules.browser.grid_helper import draw_grid_on_image, get_coordinates_from_grid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("CrucibleLoop")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

# --- State ---
browser_page = None
bot_app = None
current_objective = None
loop_active = False
workflow_memory = [] # Speichert erfolgreiche Schritte für CV-Bot

async def init_browser():
    global browser_page
    p = await async_playwright().start()
    # Wichtig: Persistent Context für Login-Erhalt
    args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
    
    context = await p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_PATH,
        headless=False,
        args=args,
        viewport={"width": 1280, "height": 800}
    )
    browser_page = context.pages[0] if context.pages else await context.new_page()
    
    await bot_app.bot.send_message(chat_id=CHAT_ID, text="🔄 Öffne AI Studio...", parse_mode='Markdown')
    await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
    await asyncio.sleep(5)
    
    # Banners wegklicken (Best Effort)
    try:
        banners = browser_page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
        if await banners.count() > 0: await banners.first.click(force=True)
    except: pass

async def consult_cloud_brain(objective, context_text=""):
    """
    Der Kern des Loops: Fragt AI Studio nach dem nächsten Schritt.
    1. Screenshot machen
    2. Upload ins AI Studio (Self-Reflexion)
    3. Prompt mit Ziel + Kontext senden
    4. Antwort extrahieren & zurückgeben
    """
    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🧠 **Konsultiere Cloud Brain...**\nKontext: {context_text[:50]}...", parse_mode='Markdown')
    
    # 1. Screenshot vom aktuellen IST-Zustand (das, was wir automatisieren wollen)
    # ACHTUNG: Wir müssen aufpassen, dass wir nicht AI Studio selbst screenshotten, wenn wir IN AI Studio sind.
    # Da wir aber aktuell AI Studio automatisieren wollen, ist das okay. 
    # Später bei Multi-Tab: Tab wechseln -> Screenshot -> Zurück zu AI Studio Tab.
    
    screen_path = "temp/loop_vision.png"
    await browser_page.screenshot(path=screen_path)
    
    try:
        # 2. Upload (Robust)
        await browser_page.keyboard.press("Escape") # Overlays weg
        await asyncio.sleep(0.5)
        
        # Finde Upload Button
        upload_btn = browser_page.locator('button[aria-label="Insert images, videos, audio, or files"]')
        if await upload_btn.count() == 0:
             # Fallback Suche
             upload_btn = browser_page.locator('button .mat-icon:has-text("add_circle")').locator('..')
        
        await upload_btn.click()
        await asyncio.sleep(1)
        
        file_input = browser_page.locator('input[type="file"]')
        await file_input.set_input_files(screen_path)
        await asyncio.sleep(2)
        
        # 3. Prompt
        prompt = f"""
Ich bin ein Automatisierungs-Agent. 
MEIN ZIEL: {objective}
AKTUELLER STATUS: {context_text}

Analysiere den Screenshot. Was muss ich als nächstes tun?
Antworte strukturiert:
1. Gedankengang (Reasoning)
2. Konkrete Aktion (Klick auf "Text", Tippe "Text", Warte, oder "Fertig")

Wenn ich klicken soll, beschreibe das Element visuell eindeutig oder nenne den Text.
"""
        textarea = browser_page.locator('textarea, div[contenteditable="true"]').last
        await textarea.fill(prompt)
        await asyncio.sleep(0.5)
        await browser_page.keyboard.press("Control+Enter") # Absenden
        
        await bot_app.bot.send_message(chat_id=CHAT_ID, text="⏳ Warte auf Antwort von Gemini...", parse_mode='Markdown')
        
        # 4. Antwort abwarten (Stop-Button Logik)
        stop_btn = browser_page.locator('button:has-text("Stop")')
        for _ in range(40): # Max 80 Sek
            await asyncio.sleep(2)
            if await stop_btn.count() == 0: break # Stop weg -> Fertig
            
        # 5. Antwort extrahieren
        # Wir holen alle Antwort-Texte und nehmen den allerletzten
        responses = await browser_page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.model-response-text, .markdown-renderer, p, .chat-message'))
                .map(e => e.innerText)
                .filter(t => t && t.trim().length > 10);
        }''')
        
        final_answer = responses[-1] if responses else "Konnte Antwort nicht lesen."
        
        return final_answer

    except Exception as e:
        return f"Fehler im Brain-Loop: {e}"

async def execute_action_from_brain(brain_response):
    """
    Versucht, die Antwort des Brains in eine Playwright-Aktion umzusetzen.
    Wenn unsicher -> Fragt User via Telegram (Magic Klick).
    """
    # Simple Heuristik: Suche nach "Klick auf..."
    # In einem echten System würde das Brain JSON zurückgeben. Hier parsen wir Text.
    
    markup = InlineKeyboardMarkup([
        [InlineKeyboardButton("✨ Magic Klick (Manuell)", callback_data='magic_click')],
        [InlineKeyboardButton("✅ Als erledigt markieren (Weiter)", callback_data='confirm_step')],
        [InlineKeyboardButton("🛑 Stop Loop", callback_data='abort')]
    ])
    
    # Zeige User das Ergebnis und frage nach Action
    await send_screenshot(f"🧠 **Brain Vorschlag:**\n\n{brain_response[:1000]}\n\nWas soll ich tun?", markup)

async def send_screenshot(caption, markup=None):
    path = "temp/view.png"
    await browser_page.screenshot(path=path)
    with open(path, "rb") as f:
        await bot_app.bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption, reply_markup=markup, parse_mode='Markdown')

# --- Telegram Handlers ---

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_objective, loop_active
    if update.effective_user.id not in ALLOWED_IDS: return
    
    text = update.message.text.strip()
    
    if text.lower() == "open":
        await init_browser()
        await bot_app.bot.send_message(chat_id=CHAT_ID, text="✅ Bereit. Nenne dein Ziel (z.B. 'Wechsle Modell').")
        
    elif not loop_active:
        # Startet den Loop
        current_objective = text
        loop_active = True
        await update.message.reply_text(f"🚀 **Starte Crucible Loop**\nZiel: `{current_objective}`", parse_mode='Markdown')
        
        # Erster Schritt: Brain fragen
        response = await consult_cloud_brain(current_objective, "Startpunkt. Analysiere UI.")
        await execute_action_from_brain(response)
        
    else:
        # Während Loop aktiv ist, nehmen wir Nachrichten als "User Feedback" / Kontext
        await update.message.reply_text(f"📝 Gebe Info an Brain weiter: `{text}`", parse_mode='Markdown')
        response = await consult_cloud_brain(current_objective, f"User Hinweis: {text}")
        await execute_action_from_brain(response)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    if query.data == 'magic_click':
        await query.edit_message_caption(caption="🪄 Generiere Magic Link...")
        path = "temp/magic.png"
        await browser_page.screenshot(path=path)
        
        coords = await get_user_click_via_magic_link(path, bot_app, CHAT_ID, "klicken")
        if coords:
            x, y = coords
            await browser_page.mouse.click(x, y)
            await query.edit_message_caption(caption=f"✅ Geklickt bei {x},{y}. Frage Brain nach nächstem Schritt...")
            
            # Loop geht weiter -> Brain fragen "Was jetzt?"
            response = await consult_cloud_brain(current_objective, f"Habe auf Koordinate {x},{y} geklickt.")
            await execute_action_from_brain(response)
            
    elif query.data == 'confirm_step':
        await query.edit_message_caption(caption="✅ Schritt bestätigt. Frage Brain nach nächstem Schritt...")
        response = await consult_cloud_brain(current_objective, "Letzter Schritt war erfolgreich. Was kommt als nächstes?")
        await execute_action_from_brain(response)
        
    elif query.data == 'abort':
        global loop_active
        loop_active = False
        await query.edit_message_caption(caption="🛑 Loop beendet.")

async def main():
    global bot_app
    if not TELEGRAM_TOKEN: return
    
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
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