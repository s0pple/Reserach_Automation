import asyncio
import os
import sys
import logging
import json
from playwright.async_api import async_playwright
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from PIL import Image

sys.path.append("/app")
from src.modules.browser.grid_helper import draw_grid_on_image, get_coordinates_from_grid
from src.modules.browser.magic_link import get_user_click_via_magic_link

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("GuidedWorkflow")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

_decision_event = asyncio.Event()
_user_decision = None
_awaiting_grid_input = False
_current_grid_size = 10
_action_mode = 'click' # kann 'click' oder 'hover' sein

bot_app = None

# Workflow Recording Memory
workflow_log = []

async def wait_for_menu_decision():
    global _user_decision, _awaiting_grid_input
    _user_decision = None
    _awaiting_grid_input = False
    _decision_event.clear()
    await _decision_event.wait()
    return _user_decision

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _user_decision, _awaiting_grid_input, _current_grid_size, _action_mode
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    if query.data == 'grid_10':
        _current_grid_size = 10
        _action_mode = 'click'
        _awaiting_grid_input = True
        await query.edit_message_caption(caption="🎯 **Klick-Modus (10x10)**\nSende Koordinate zum KLICKEN (z.B. `B4`).", parse_mode='Markdown')
        return
    elif query.data == 'grid_20':
        _current_grid_size = 20
        _action_mode = 'click'
        _awaiting_grid_input = True
        await query.edit_message_caption(caption="🔍 **Fein-Klick (20x20)**\nSende Koordinate zum KLICKEN (z.B. `B14`).", parse_mode='Markdown')
        return
    elif query.data == 'hover_10':
        _current_grid_size = 10
        _action_mode = 'hover'
        _awaiting_grid_input = True
        await query.edit_message_caption(caption="🖱️ **Hover-Modus (10x10)**\nSende Koordinate zum HOVERN (ohne Klick) (z.B. `B8`).", parse_mode='Markdown')
        return
    elif query.data == 'hover_20':
        _current_grid_size = 20
        _action_mode = 'hover'
        _awaiting_grid_input = True
        await query.edit_message_caption(caption="🖱️ **Fein-Hover (20x20)**\nSende Koordinate zum HOVERN (ohne Klick) (z.B. `B14`).", parse_mode='Markdown')
        return

    _user_decision = query.data
    try:
        await query.edit_message_caption(caption=f"✅ Gewählt: `{_user_decision}`", parse_mode='Markdown')
    except: pass
    _decision_event.set()

async def handle_text(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _user_decision, _awaiting_grid_input, _action_mode
    if not _awaiting_grid_input: return
    if update.effective_user.id not in ALLOWED_IDS: return
    
    text = update.message.text.strip().upper()
    if len(text) >= 2 and text[0].isalpha() and text[1:].isdigit():
        _user_decision = f"GRID:{text}:{_action_mode}"
        _awaiting_grid_input = False
        action_verb = "Klicke auf" if _action_mode == 'click' else "Hovere über"
        await update.message.reply_text(f"🚀 {action_verb} `{text}`...", parse_mode='Markdown')
        _decision_event.set()
    else:
        await update.message.reply_text("❌ Format ungültig. Sende z.B. `C5`.")

def save_crop_for_workflow(image_path, x, y, label, action_mode):
    """Schneidet ein kleines Bild um die Klick/Hover-Koordinate aus und speichert es fürs Workflow-Recording."""
    try:
        if not os.path.exists("temp/workflow"):
            os.makedirs("temp/workflow")
            
        with Image.open(image_path) as img:
            # 100x100 Pixel Ausschnitt
            left = max(0, x - 50)
            top = max(0, y - 50)
            right = min(img.width, x + 50)
            bottom = min(img.height, y + 50)
            
            crop_img = img.crop((left, top, right, bottom))
            crop_path = f"temp/workflow/step_{len(workflow_log)}_{action_mode}_{label}.png"
            crop_img.save(crop_path)
            
            # Log speichern
            workflow_log.append({
                "step": len(workflow_log),
                "action": action_mode,
                "label": label,
                "x": x,
                "y": y,
                "template_image": crop_path
            })
            
            # Speichere auch das json log
            with open("temp/workflow/workflow_log.json", "w") as f:
                json.dump(workflow_log, f, indent=4)
                
            return crop_path
    except Exception as e:
        logger.error(f"Konnte Crop nicht speichern: {e}")
        return None

async def send_main_menu(page):
    path = "temp/main_view.png"
    grid_path = "temp/main_grid.png"
    
    await page.screenshot(path=path)
    draw_grid_on_image(path, grid_path, _current_grid_size)
    
    buttons = [
        [InlineKeyboardButton("✨ Magic Klick (Direkt im Browser)", callback_data='magic_click')],
        [InlineKeyboardButton("✨ Magic Hover (Direkt im Browser)", callback_data='magic_hover')],
        [InlineKeyboardButton("🎯 Klick (10x10)", callback_data='grid_10'), InlineKeyboardButton("🎯 Klick (20x20)", callback_data='grid_20')],
        [InlineKeyboardButton("🖱️ Hover (10x10)", callback_data='hover_10'), InlineKeyboardButton("🖱️ Hover (20x20)", callback_data='hover_20')],
        [InlineKeyboardButton("📤 Macro: Upload", callback_data='macro_upload'), InlineKeyboardButton("📖 Macro: Lesen", callback_data='macro_read')],
        [InlineKeyboardButton("🔄 Refresh", callback_data='refresh'), InlineKeyboardButton("🛑 Beenden", callback_data='abort')]
    ]
    reply_markup = InlineKeyboardMarkup(buttons)
    
    with open(grid_path, "rb") as f:
        await bot_app.bot.send_photo(
            chat_id=CHAT_ID, 
            photo=f, 
            caption="🎮 **Cockpit:** Was ist der nächste Schritt?", 
            reply_markup=reply_markup, 
            parse_mode='Markdown'
        )

async def run_guided_workflow():
    await bot_app.bot.send_message(chat_id=CHAT_ID, text="🚀 **Geführter Workflow gestartet!**\nLade AI Studio...", parse_mode='Markdown')
    
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
        
        await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await page.wait_for_timeout(5000)
        
        try:
            banners = page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
            if await banners.count() > 0: await banners.first.click(force=True)
        except: pass

        while True:
            await send_main_menu(page)
            decision = await wait_for_menu_decision()
            
            if decision == 'abort':
                await bot_app.bot.send_message(chat_id=CHAT_ID, text="🛑 Session beendet. Workflow Log gespeichert in temp/workflow/")
                break
                
            elif decision == 'refresh':
                continue # Loop schickt automatisch neues Menü
                
            elif decision == 'macro_upload':
                await bot_app.bot.send_message(chat_id=CHAT_ID, text="⚙️ Führe Upload Macro aus...")
                try:
                    img_path = "temp/screen_to_analyze.png"
                    await page.screenshot(path=img_path)
                    
                    await page.locator('button[aria-label="Insert images, videos, audio, or files"]').click()
                    await page.wait_for_timeout(1000)
                    
                    file_input = page.locator('input[type="file"]')
                    await file_input.set_input_files(img_path)
                    await page.wait_for_timeout(2000)
                    
                    textarea = page.locator('textarea, div[contenteditable="true"]').last
                    await textarea.fill("Analyze this screenshot of the Google AI Studio UI. I want to change the selected model. Describe exactly which button or area I need to click first, and where it is located on the screen.")
                    await page.keyboard.press("Control+Enter")
                    
                    await bot_app.bot.send_message(chat_id=CHAT_ID, text="✅ Upload erfolgreich! Warte ca. 15 Sekunden, lade Screenshot neu und wähle dann 'Antwort auslesen'.")
                except Exception as e:
                    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"❌ Fehler im Macro: {e}")
                    
            elif decision == 'macro_read':
                await bot_app.bot.send_message(chat_id=CHAT_ID, text="📖 Lese Antwort aus...")
                try:
                    responses = await page.locator('chat-message, .model-response-text, .markdown-renderer').all_inner_texts()
                    last_response = ""
                    for resp in reversed(responses):
                        if resp.strip() and len(resp.strip()) > 50:
                            last_response = resp.strip()
                            break
                    if not last_response:
                        last_response = await page.locator('body').inner_text()
                        last_response = last_response[-1500:]
                        
                    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🧠 **Gefundene Antwort:**\n\n`{last_response[:3000]}`", parse_mode='Markdown')
                except Exception as e:
                    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"❌ Fehler beim Lesen: {e}")
                    
            elif decision in ['magic_click', 'magic_hover']:
                action = 'click' if decision == 'magic_click' else 'hover'
                action_verb = 'klicken' if action == 'click' else 'hovern'
                
                clean_img = "temp/main_view.png" # already taken in send_main_menu
                coords = await get_user_click_via_magic_link(clean_img, bot_app, CHAT_ID, action_verb)
                
                if coords:
                    x, y = coords[0], coords[1]
                    label = f"magic_{x}_{y}"
                    crop_saved = save_crop_for_workflow(clean_img, x, y, label, action)
                    
                    if action == "hover":
                        await page.mouse.move(x, y)
                        await page.wait_for_timeout(1000)
                        await bot_app.bot.send_message(chat_id=CHAT_ID, text="🖱️ Maus hovert jetzt. (Template gespeichert!)")
                    else:
                        await page.mouse.click(x, y)
                        await page.wait_for_timeout(2000)
                        await bot_app.bot.send_message(chat_id=CHAT_ID, text="🎯 Klick ausgeführt. (Template gespeichert!)")
                else:
                    await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Magic Link abgebrochen oder fehlgeschlagen.")

            elif decision and decision.startswith("GRID:"):
                # Format: GRID:B4:hover oder GRID:B4:click
                parts = decision.split(":")
                tile = parts[1]
                action = parts[2] if len(parts) > 2 else "click"
                
                viewport = page.viewport_size
                coords = get_coordinates_from_grid(tile, viewport['width'], viewport['height'], _current_grid_size)
                if coords:
                    x, y = coords[0], coords[1]
                    
                    clean_bg = "temp/pre_action_clean.png"
                    await page.screenshot(path=clean_bg)
                    crop_saved = save_crop_for_workflow(clean_bg, x, y, tile, action)
                    
                    if action == "hover":
                        await page.mouse.move(x, y)
                        await page.wait_for_timeout(1000)
                        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🖱️ Maus hovert jetzt über {tile}. (Template gespeichert!)")
                    else:
                        await page.mouse.click(x, y)
                        await page.wait_for_timeout(2000)
                        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🎯 Klick auf {tile} ausgeführt. (Template gespeichert!)")
                        
                else:
                    await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Konnte Koordinaten nicht berechnen.")

        await context.close()

async def main():
    global bot_app
    if not TELEGRAM_TOKEN or not CHAT_ID: return
    
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text))
    
    await bot_app.initialize()
    await bot_app.start()
    await bot_app.updater.start_polling(drop_pending_updates=True)
    
    try:
        await run_guided_workflow()
    finally:
        await bot_app.updater.stop()
        await bot_app.stop()
        await bot_app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())