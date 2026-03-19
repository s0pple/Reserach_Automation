import asyncio
import os
import sys
import logging
from playwright.async_api import async_playwright
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image

sys.path.append("/app")
from src.modules.browser.grid_helper import draw_grid_on_image, get_coordinates_from_grid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIStudioCV")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

_user_decision = None
_decision_event = asyncio.Event()
_awaiting_grid_input = False
_current_grid_size = 10
bot_app = None

async def send_msg_to_tg(text):
    if not bot_app: return
    try:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text=text, parse_mode='Markdown')
    except Exception as e:
        logger.error(f"TG Msg Error: {e}")

async def send_screenshot_to_tg(page, caption=""):
    if not bot_app: return
    path = "temp/current_view.png"
    try:
        await page.screenshot(path=path)
        with open(path, "rb") as f:
            await bot_app.bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption)
    except Exception as e:
        logger.error(f"TG Screenshot Error: {e}")

async def wait_for_human_help(screenshot_path: str, error_context: str, bot_instance, chat_id: str, buttons=None) -> str:
    global _user_decision, _awaiting_grid_input
    _user_decision = None
    _decision_event.clear()
    _awaiting_grid_input = False

    if buttons is None:
        buttons = [
            [InlineKeyboardButton("🎯 Manueller Grid-Klick", callback_data='grid_click')],
            [InlineKeyboardButton("🔎 Feineres Grid", callback_data='finer_grid')],
            [InlineKeyboardButton("⏭️ Skip (Ignorieren)", callback_data='skip')],
            [InlineKeyboardButton("🛑 Abbrechen", callback_data='abort')]
        ]
    
    reply_markup = InlineKeyboardMarkup(buttons)
    caption = f"🚨 **Hilfe / Input benötigt!**\n\n**Kontext:** {error_context}"
    
    if screenshot_path and os.path.exists(screenshot_path):
        with open(screenshot_path, 'rb') as photo:
            await bot_instance.send_photo(chat_id=chat_id, photo=photo, caption=caption, reply_markup=reply_markup, parse_mode='Markdown')
    else:
        await bot_instance.send_message(chat_id=chat_id, text=caption, reply_markup=reply_markup, parse_mode='Markdown')

    await _decision_event.wait()
    return _user_decision

async def human_decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _user_decision, _awaiting_grid_input
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS:
        await query.answer("Unauthorized", show_alert=True)
        return
    await query.answer()
    
    if query.data == 'grid_click':
        _awaiting_grid_input = True
        try:
            await query.edit_message_caption(caption="📐 **Grid Modus aktiviert!**\nSende mir jetzt die Kachel-Koordinate (z.B. `B4` oder `H9`), wohin ich klicken soll.", parse_mode='Markdown')
        except:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text="📐 **Grid Modus aktiviert!**\nSende mir jetzt die Kachel-Koordinate (z.B. `B4` oder `H9`), wohin ich klicken soll.", parse_mode='Markdown')
        return # Blockiere weiter, warte auf Text-Nachricht!
        
    _user_decision = query.data
    
    try:
        await query.edit_message_caption(caption=f"✅ Entscheidung: `{_user_decision}`", parse_mode='Markdown')
    except:
        await query.edit_message_text(text=f"✅ Entscheidung: `{_user_decision}`", parse_mode='Markdown')
        
    _decision_event.set()

async def text_message_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _user_decision, _awaiting_grid_input
    if not _awaiting_grid_input:
        return
    if update.effective_user.id not in ALLOWED_IDS:
        return
        
    text = update.message.text.strip().upper()
    if len(text) >= 2 and text[0].isalpha() and text[1:].isdigit():
        _user_decision = f"GRID:{text}"
        _awaiting_grid_input = False
        await update.message.reply_text(f"🎯 Klicke auf Kachel `{text}`...", parse_mode='Markdown')
        _decision_event.set()
    else:
        await update.message.reply_text("❌ Ungültiges Format. Bitte sende Buchstabe+Zahl (z.B. `C5`).")

async def aistudio_conveyor():
    global _current_grid_size
    print("🏭 Start AI Studio Conveyor...")
    await send_msg_to_tg("🚀 **AI Studio Vision Loop gestartet**\nVerbinde mit Browser...")
    
    async with async_playwright() as p:
        args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
        
        context = await p.chromium.launch_persistent_context(
            user_data_dir=PROFILE_PATH,
            headless=False,
            args=args,
            viewport={"width": 1280, "height": 800}
        )
        
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            # Step 1: Open AI Studio
            await send_msg_to_tg("🔄 Lade AI Studio...")
            await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
            await page.wait_for_timeout(5000)
            
            try:
                banners = page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
                if await banners.count() > 0:
                    await banners.first.click(force=True)
            except: pass

            await send_screenshot_to_tg(page, "✅ AI Studio geladen. Ich werde jetzt AI Studio selbst fragen, wie ich das Modell wechsle!")

            # Step 2: Upload Screenshot to itself
            test_img_path = "temp/screen_to_analyze.png"
            await page.screenshot(path=test_img_path)
            
            try:
                # Menü öffnen
                await page.locator('button[aria-label="Insert images, videos, audio, or files"]').click()
                await page.wait_for_timeout(1000)
                
                # File Input füttern
                file_input = page.locator('input[type="file"]')
                await file_input.set_input_files(test_img_path)
                await page.wait_for_timeout(2000)
                
                # Prompt schreiben
                prompt = "Analyze this screenshot of the Google AI Studio UI. I want to change the selected model. Describe exactly which button or area I need to click first, and where it is located on the screen."
                textarea = page.locator('textarea, div[contenteditable="true"]').last
                await textarea.fill(prompt)
                await page.keyboard.press("Control+Enter")
                
                await send_msg_to_tg("📤 Screenshot hochgeladen und Frage gestellt. Warte auf Antwort von Gemini (20 Sekunden)...")
                
            except Exception as e:
                await send_msg_to_tg(f"❌ Fehler beim Upload: {e}")
                return

            # Wait for Answer
            await page.wait_for_timeout(20000)
            
            # Robuste Textextraktion
            last_response = ""
            try:
                # Mehrere Selectors probieren
                responses = await page.locator('chat-message, .model-response-text, .markdown-renderer').all_inner_texts()
                for resp in reversed(responses):
                    if resp.strip() and len(resp.strip()) > 50:
                        last_response = resp.strip()
                        break
            except: pass
            
            if not last_response:
                # Fallback: Den ganzen Text nehmen und das Ende abscheiden
                body_text = await page.locator('body').inner_text()
                last_response = body_text[-1500:] + "\n[FALLBACK EXTRACTION]"
            
            await send_screenshot_to_tg(page, f"🧠 **Gemini's Antwort:**\n\n{last_response[:1000]}")
            
            # Step 3: Ask User how to proceed mit Grid-Loop
            _current_grid_size = 10
            
            while True:
                grid_path = f"temp/current_grid_{_current_grid_size}.png"
                draw_grid_on_image("temp/current_view.png", grid_path, _current_grid_size)
                
                decision = await wait_for_human_help(
                    grid_path, 
                    "Wie sollen wir basierend auf Geminis Antwort vorgehen?", 
                    bot_app.bot, 
                    CHAT_ID,
                    buttons=[
                        [InlineKeyboardButton("⚙️ Automatischer Fast-Path (Versuch)", callback_data='fast_path')],
                        [InlineKeyboardButton("🎯 Manueller Grid-Klick", callback_data='grid_click')],
                        [InlineKeyboardButton("🔎 Feineres Grid", callback_data='finer_grid')],
                        [InlineKeyboardButton("🛑 Beenden", callback_data='abort')]
                    ]
                )
                
                if decision == 'finer_grid':
                    _current_grid_size = 20 if _current_grid_size == 10 else 30
                    await send_msg_to_tg(f"🔄 Generiere Grid mit Größe {_current_grid_size}x{_current_grid_size}...")
                    continue # Loop wiederholen mit neuem Grid
                else:
                    break # Loop verlassen für die Aktion
            
            if decision == 'abort':
                await send_msg_to_tg("🛑 Session beendet.")
                return
            elif decision == 'fast_path':
                await send_msg_to_tg("🛠️ Versuche Fast-Path: Klicke auf 'model-selector-card'...")
                try:
                    await page.locator('div.model-selector-card').click(timeout=3000)
                    await page.wait_for_timeout(2000)
                    await send_screenshot_to_tg(page, "Ist das Menü jetzt offen? (Fast-Path erfolgreich)")
                except Exception as e:
                    await send_msg_to_tg(f"❌ Fast-Path gescheitert: {e}")
            elif decision and decision.startswith("GRID:"):
                tile = decision.split(":")[1]
                viewport = page.viewport_size
                coords = get_coordinates_from_grid(tile, viewport['width'], viewport['height'], _current_grid_size)
                if coords:
                    await send_msg_to_tg(f"🖱️ Klicke auf Kachel {tile}...")
                    await page.mouse.click(coords[0], coords[1])
                    await page.wait_for_timeout(2000)
                    await send_screenshot_to_tg(page, "✅ Klick ausgeführt. Neues Menü offen?")
                
        except Exception as e:
            await send_msg_to_tg(f"💥 Fataler Fehler: {e}")
        finally:
            await context.close()

async def main():
    global bot_app
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("No Telegram Token or Chat ID")
        return
    
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CallbackQueryHandler(human_decision_handler))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_message_handler))
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    
    try:
        await aistudio_conveyor()
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())