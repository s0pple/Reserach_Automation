import asyncio
import os
import sys
import logging
import re
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes

sys.path.append("/app")
from src.modules.browser.magic_link import get_user_click_via_magic_link
from src.modules.browser.grid_helper import draw_grid_on_image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PhalanxOrchestrator")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

# Global state
browser_page = None
bot_app = None
current_goal = None

async def send_screenshot(caption, buttons=None):
    path = "temp/phalanx_view.png"
    await browser_page.screenshot(path=path)
    
    markup = None
    if buttons:
        markup = InlineKeyboardMarkup(buttons)
        
    with open(path, "rb") as f:
        await bot_app.bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption, reply_markup=markup, parse_mode='Markdown')

async def init_browser():
    global browser_page
    logger.info("Starte Browser...")
    p = await async_playwright().start()
    args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
    
    context = await p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_PATH,
        headless=False,
        args=args,
        viewport={"width": 1280, "height": 800}
    )
    browser_page = context.pages[0] if context.pages else await context.new_page()

async def execute_ai_planning_step(goal, is_retry=False, last_error=None):
    """Lädt Screenshot hoch, fragt AI nach dem nächsten Klick und führt ihn aus."""
    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🕵️ **KI analysiert UI...**\nZiel: `{goal}`\nMache Screenshot und frage das AI Studio Brain...", parse_mode='Markdown')
    
    # 1. Screenshot machen
    state_img = "temp/state_for_ai.png"
    await browser_page.screenshot(path=state_img)
    
    try:
        # 2. Upload
        # Escape drücken, um etwaige offene Dropdowns/Overlays zu schließen
        await browser_page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        
        await browser_page.locator('button[aria-label="Insert images, videos, audio, or files"]').click(force=True)
        await asyncio.sleep(1)
        await browser_page.locator('input[type="file"]').set_input_files(state_img)
        await asyncio.sleep(2)
        
        # 3. Prompt generieren
        if is_retry:
            prompt = f"""
ZIEL: {goal}
Wir automatisieren dieses UI. Dies ist der NEUE Screenshot nach unserem letzten Versuch.
Wir sind steckengeblieben. Letzter Fehler/Status: {last_error or 'Aktion nicht gefunden oder fehlgeschlagen.'}
Was ist der nächste Schritt? 
Erkläre deine Gedankengänge kurz. 
Wenn ich etwas klicken soll, gib mir EXAKT den sichtbaren Text des Elements in einem Block, der mit ```click beginnt.
Beispiel:
```click
Gemini 3 Flash Preview
```
"""
        else:
            prompt = f"""
ZIEL: {goal}
Wir automatisieren dieses UI. Analysiere den Screenshot. 
Was ist der nächste Schritt, um das Ziel zu erreichen?
Erkläre deine Gedankengänge kurz. 
Wenn ich etwas klicken soll, gib mir EXAKT den sichtbaren Text des Elements in einem Block, der mit ```click beginnt.
Beispiel:
```click
Gemini 3 Flash Preview
```
Wenn keine Aktion offensichtlich ist, erkläre kurz warum.
"""
        textarea = browser_page.locator('textarea, div[contenteditable="true"]').last
        await textarea.fill(prompt)
        await asyncio.sleep(0.5) # Kurzer Delay vor dem Absenden
        await browser_page.keyboard.press("Control+Enter")
        
        await bot_app.bot.send_message(chat_id=CHAT_ID, text="⏳ Frage gestellt. Warte auf Antwort (dynamisch)...")
        
        # 4. Dynamisches Warten (auf den Stop-Button)
        try:
            await asyncio.sleep(2)
            stop_btn = browser_page.locator('button:has-text("Stop")')
            for _ in range(30):
                if await stop_btn.count() == 0 or not await stop_btn.is_visible():
                    break
                await asyncio.sleep(2)
        except Exception as wait_e:
            logger.warning(f"Dynamisches Warten fehlgeschlagen: {wait_e}")
            await asyncio.sleep(15)
        
        await asyncio.sleep(1)
        
        # 5. Antwort lesen (robuste JS-Extraktion)
        texts = await browser_page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.model-response-text, .markdown-renderer, p, .chat-message'))
                .map(e => e.innerText)
                .filter(t => t && t.trim().length > 20);
        }''')
        
        last_response = texts[-1] if texts else "Konnte keine Antwort auslesen."
        
        # IMMER die Antwort an den User senden, damit der Kontext/Reasoning nicht verloren geht!
        clean_text = last_response[:2000].replace('```', "'''")
        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🧠 **AI Studio Reasoning:**\n\n{clean_text}", parse_mode='Markdown')
                
        # 6. Aktion extrahieren (ACHTUNG: checkt nach dem geänderten Markdown Block)
        click_match = re.search(r"'''click\n(.*?)\n'''", clean_text, re.DOTALL) or re.search(r'```click\n(.*?)\n```', last_response, re.DOTALL)
        
        if click_match:
            element_text = click_match.group(1).strip()
            await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🤖 **KI-Entscheidung:** Ich soll auf `{element_text}` klicken.\nFühre aus...", parse_mode='Markdown')
            
            try:
                # Versuche zu klicken
                await browser_page.locator(f'text="{element_text}"').first.click(timeout=3000)
                await asyncio.sleep(2)
                
                buttons = [
                    [InlineKeyboardButton("🔄 KI nächsten Schritt planen lassen", callback_data='ai_step')],
                    [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
                    [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
                    [InlineKeyboardButton("🛑 Workflow Beenden", callback_data='abort')]
                ]
                await send_screenshot(f"✅ Klick auf '{element_text}' ausgeführt.\nHat es geklappt?", buttons)
                
            except Exception as e:
                buttons = [
                    [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
                    [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
                    [InlineKeyboardButton("🛑 Abbrechen", callback_data='abort')]
                ]
                await send_screenshot(f"❌ Klick auf '{element_text}' fehlgeschlagen: {str(e)[:100]}.\nBitte übernimm die Kontrolle!", buttons)
                
        else:
            buttons = [
                [InlineKeyboardButton("🔄 Nochmal Fragen", callback_data='ai_step')],
                [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
                [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
                [InlineKeyboardButton("🛑 Abbrechen", callback_data='abort')]
            ]
            await send_screenshot(f"🤖 **Kein automatischer Klick gefunden.** Was nun?", buttons)

    except Exception as e:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"💥 Fehler im KI-Loop: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_goal
    if update.effective_user.id not in ALLOWED_IDS: return
    
    text = update.message.text.strip()
    
    if text.lower() == "open aistudio" or text.lower() == "öffne aistudio":
        await update.message.reply_text("🔄 Öffne AI Studio...", parse_mode='Markdown')
        await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await asyncio.sleep(5)
        
        buttons = [
            [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
            [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
            [InlineKeyboardButton("📤 Macro: UI an KI übergeben", callback_data='ai_step')]
        ]
        await send_screenshot("✅ AI Studio geladen. Was ist das Ziel?", buttons)
    else:
        current_goal = text
        await execute_ai_planning_step(current_goal)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_goal
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    decision = query.data
    
    if decision == 'refresh':
        await query.edit_message_caption(caption="📸 Lade neuen Screenshot...")
        buttons = [
            [InlineKeyboardButton("🔄 KI analysieren lassen", callback_data='ai_step')],
            [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
            [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
            [InlineKeyboardButton("🛑 Beenden", callback_data='abort')]
        ]
        await send_screenshot("📸 Ansicht aktualisiert. Was ist der nächste Schritt?", buttons)
        
    if decision == 'ai_step':
        await query.edit_message_caption(caption="🔄 Starte nächste KI-Iteration (Neuer Screenshot)...")
        # Hier ist es immer ein Retry mit dem Kontext des aktuellen Screens
        await execute_ai_planning_step(current_goal or "Analysiere UI und fahre fort", is_retry=True, last_error="Bitte fahre fort basierend auf dem aktuellen Screen.")
        
    elif decision in ['magic_click', 'magic_hover']:
        action_verb = "klicken" if decision == 'magic_click' else "hovern"
        await query.edit_message_caption(caption=f"🪄 Generiere Magic Link zum {action_verb}...")
        
        path = "temp/magic_view.png"
        await browser_page.screenshot(path=path)
        
        coords = await get_user_click_via_magic_link(path, bot_app, CHAT_ID, action_verb)
        
        if coords:
            x, y = coords
            if decision == 'magic_click':
                await browser_page.mouse.click(x, y)
                await asyncio.sleep(2)
            else:
                await browser_page.mouse.move(x, y)
                await asyncio.sleep(1)
                
            buttons = [
                [InlineKeyboardButton("🔄 KI analysieren lassen", callback_data='ai_step')],
                [InlineKeyboardButton("✨ Weiterer Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Weiterer Magic Hover", callback_data='magic_hover')],
                [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
                [InlineKeyboardButton("🛑 Beenden", callback_data='abort')]
            ]
            await send_screenshot(f"✅ Magic Aktion bei X:{x}, Y:{y} ausgeführt.\nWas ist der nächste Schritt?", buttons)
        else:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Magic Link abgebrochen.")
            
    elif decision == 'abort':
        await query.edit_message_caption(caption="🛑 Workflow beendet.")
        current_goal = None

async def main():
    global bot_app
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("Telegram Config fehlt.")
        return
        
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    await init_browser()
    
    await bot_app.bot.send_message(
        chat_id=CHAT_ID, 
        text="🚀 **Phalanx Orchestrator (Clean Mode) Online!**\n\nSchreibe `open aistudio` um den Browser zu laden.\nDanach schreibst du einfach dein Ziel, z.B. `Wechsle Modell zu Gemini 3.1 Pro`.",
        parse_mode='Markdown'
    )
    
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