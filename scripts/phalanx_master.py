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
from src.tools.general.session_tool import interactive_session_tool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PhalanxMaster")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

# Global state
browser_page = None
bot_app = None
current_goal = None
_cli_session_id = None
last_ai_studio_response = None

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

async def get_cli_response_callback(text):
    """Callback-Funktion, die den Output der CLI-Session an Telegram weiterleitet."""
    try:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"💻 **CLI Agent:**\n```text\n{text[:3500]}\n```", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Failed to send CLI callback to TG: {e}")

async def ensure_cli_session():
    """Startet gemini-cli im Hintergrund, falls noch nicht aktiv."""
    global _cli_session_id
    if not _cli_session_id:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text="💻 Starte lokalen `gemini-cli` Agenten als Task-Manager...")
        result = await interactive_session_tool(
            action="start", 
            command="gemini-cli --system 'Du bist der Phalanx-Manager. Du hältst den Plan, listest verfügbare Tools auf und steuerst den Prozess.'", 
            telegram_callback=get_cli_response_callback
        )
        if "session_id" in result:
            _cli_session_id = result["session_id"]
        else:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"❌ Konnte CLI nicht starten: {result}")

async def ask_cli_agent(instruction):
    """Sendet Input an die laufende CLI Session."""
    await ensure_cli_session()
    if _cli_session_id:
        await interactive_session_tool(action="input", session_id=_cli_session_id, input_text=instruction)

async def execute_ai_planning_step(goal, is_retry=False, last_error=None):
    """Lädt Screenshot hoch, fragt AI nach dem nächsten Schritt."""
    global last_ai_studio_response
    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🕵️ **KI analysiert UI...**\nFrage AI Studio nach Input...", parse_mode='Markdown')
    
    # 1. Screenshot machen
    state_img = "temp/state_for_ai.png"
    await browser_page.screenshot(path=state_img)
    
    try:
        # 2. Upload
        await browser_page.keyboard.press("Escape")
        await asyncio.sleep(0.5)
        
        await browser_page.locator('button[aria-label="Insert images, videos, audio, or files"]').click(force=True)
        await asyncio.sleep(1)
        await browser_page.locator('input[type="file"]').set_input_files(state_img)
        await asyncio.sleep(2)
        
        # 3. Prompt generieren
        if is_retry:
            prompt = f"Wir sind steckengeblieben bei Ziel: '{goal}'. Dies ist der neue Screenshot. Letzter Status: {last_error or 'Aktion nicht gefunden.'} Erkläre mir, was ich im UI sehe und was ich als nächstes tun soll."
        else:
            prompt = f"Unser Ziel ist: '{goal}'. Analysiere den Screenshot. Was sehe ich hier und was ist der exakte nächste Schritt, den wir tun müssen, um das Ziel zu erreichen? Erkläre deine Gedankengänge kurz."
            
        textarea = browser_page.locator('textarea, div[contenteditable="true"]').last
        await textarea.fill(prompt)
        await asyncio.sleep(0.5)
        await browser_page.keyboard.press("Control+Enter")
        
        await bot_app.bot.send_message(chat_id=CHAT_ID, text="⏳ Frage gestellt. Warte auf AI Studio Antwort...")
        
        # 4. Dynamisches Warten
        try:
            await asyncio.sleep(2)
            stop_btn = browser_page.locator('button:has-text("Stop")')
            for _ in range(30):
                if await stop_btn.count() == 0 or not await stop_btn.is_visible():
                    break
                await asyncio.sleep(2)
        except Exception as wait_e:
            await asyncio.sleep(15)
        
        await asyncio.sleep(1)
        
        # 5. Antwort lesen
        texts = await browser_page.evaluate('''() => {
            return Array.from(document.querySelectorAll('.model-response-text, .markdown-renderer, p, .chat-message'))
                .map(e => e.innerText)
                .filter(t => t && t.trim().length > 20);
        }''')
        
        last_ai_studio_response = texts[-1] if texts else "Konnte keine Antwort auslesen."
        clean_text = last_ai_studio_response[:2000].replace('```', "'''")
        
        # Dem User zeigen, was AI Studio gesagt hat, und Optionen für den Workflow geben
        buttons = [
            [InlineKeyboardButton("📤 Antwort an CLI-Manager senden", callback_data='send_to_cli')],
            [InlineKeyboardButton("🔄 Nochmal AI Studio fragen (Neu)", callback_data='ai_step')],
            [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
            [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
            [InlineKeyboardButton("🛑 Beenden", callback_data='abort')]
        ]
        await send_screenshot(f"🧠 **AI Studio Reasoning:**\n\n{clean_text}\n\nWas nun?", buttons)

    except Exception as e:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"💥 Fehler im KI-Loop: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_goal
    if update.effective_user.id not in ALLOWED_IDS: return
    
    text = update.message.text.strip()
    
    if text.lower() == "open aistudio":
        await update.message.reply_text("🔄 Öffne AI Studio...", parse_mode='Markdown')
        await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await asyncio.sleep(5)
        
        # CLI Starten, wenn UI offen ist
        await ensure_cli_session()
        
        buttons = [
            [InlineKeyboardButton("📤 Ziel an CLI senden", callback_data='start_cli_goal')],
            [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')]
        ]
        await send_screenshot("✅ AI Studio & CLI Agent geladen. Was ist das Ziel?", buttons)
    else:
        # Alles andere wird direkt an die CLI weitergeleitet
        if _cli_session_id:
            await ask_cli_agent(text)
        else:
            current_goal = text
            await update.message.reply_text(f"Ziel gesetzt: `{current_goal}`. Klicke auf 'Ziel an CLI senden' oder drücke 'Magic Klick'.", parse_mode='Markdown')

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_goal, last_ai_studio_response
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    decision = query.data
    
    if decision == 'refresh':
        buttons = [
            [InlineKeyboardButton("🔄 AI Studio analysieren lassen", callback_data='ai_step')],
            [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
            [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')]
        ]
        await send_screenshot("📸 Ansicht aktualisiert. Was ist der nächste Schritt?", buttons)
        
    elif decision == 'start_cli_goal':
        if not current_goal:
            await query.edit_message_caption(caption="❌ Kein Ziel gesetzt. Schreibe erst einen Text in den Chat.")
            return
        await query.edit_message_caption(caption="💻 Sende Ziel an CLI-Manager...")
        await ask_cli_agent(f"Unser neues Ziel ist: '{current_goal}'. Bitte erstelle einen Plan und teile mir mit, ob wir einen Workflow erstellen müssen oder ob du die Tools bereits kennst. Wenn du nicht weiter weißt, bitte mich, das AI Studio UI nach Rat zu fragen.")
        
    elif decision == 'send_to_cli':
        if last_ai_studio_response:
            await query.edit_message_caption(caption="💻 Sende AI Studio Erkenntnisse an CLI-Manager...")
            await ask_cli_agent(f"Hier ist der Output von AI Studio (Vision Analyse unseres UI's):\n\n{last_ai_studio_response}\n\nWas sollen wir als nächstes tun? Sag mir, ob du einen Playwright/CV-Befehl ausführen kannst oder ob ich manuell eingreifen soll.")
        else:
            await query.edit_message_caption(caption="❌ Keine Antwort vorhanden.")
            
    elif decision == 'ai_step':
        await query.edit_message_caption(caption="🔄 Lade UI-Screenshot ins AI Studio...")
        await execute_ai_planning_step(current_goal or "Analysiere UI", is_retry=True)
        
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
                [InlineKeyboardButton("🔄 AI Studio Ergebnis analysieren lassen", callback_data='ai_step')],
                [InlineKeyboardButton("✨ Weiterer Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Weiterer Magic Hover", callback_data='magic_hover')],
                [InlineKeyboardButton("📸 Screenshot Refresh", callback_data='refresh')],
                [InlineKeyboardButton("🛑 Beenden", callback_data='abort')]
            ]
            await send_screenshot(f"✅ Magic Aktion bei X:{x}, Y:{y} ausgeführt.\nWas ist der nächste Schritt?", buttons)
            
            # Teile der CLI mit, dass eine manuelle Aktion durchgeführt wurde
            await ask_cli_agent(f"Ich habe soeben manuell einen {action_verb} bei X:{x}, Y:{y} ausgeführt. Bitte merke dir diesen Schritt für unseren Workflow.")
        else:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Magic Link abgebrochen.")
            
    elif decision == 'abort':
        await query.edit_message_caption(caption="🛑 Workflow beendet.")
        current_goal = None

async def main():
    global bot_app
    if not TELEGRAM_TOKEN or not CHAT_ID:
        return
        
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    await init_browser()
    
    await bot_app.bot.send_message(
        chat_id=CHAT_ID, 
        text="🚀 **Phalanx Master (CLI + AI Studio Hybrid) Online!**\n\nSchreibe `open aistudio` um den Browser und den lokalen CLI-Manager zu laden.",
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