import asyncio
import os
import sys
import logging
from playwright.async_api import async_playwright
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes
from PIL import Image

sys.path.append("/app")
from src.modules.browser.grid_helper import draw_grid_on_image, get_coordinates_from_grid

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("InteractiveCV")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

# Global Queue für Befehle aus Telegram
cmd_queue = asyncio.Queue()
_current_grid_size = 10

async def handle_tg_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ALLOWED_IDS: return
    text = update.message.text.strip()
    await cmd_queue.put(text)
    # Kleines Feedback, dass der Befehl in der Queue ist
    try:
        await update.message.reply_text(f"⏳ Befehl eingereiht: `{text}`", parse_mode='Markdown')
    except: pass

async def send_screenshot(page, bot, caption="", grid_size=None):
    path = "temp/view.png"
    await page.screenshot(path=path)
    if grid_size:
        draw_grid_on_image(path, path, grid_size)
    with open(path, "rb") as f:
        await bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption)

async def browser_loop(bot):
    global _current_grid_size
    await bot.send_message(
        chat_id=CHAT_ID, 
        text="🚀 **Interaktiver Browser (REPL) gestartet.**\nDer Browser bleibt jetzt offen und hört auf deine Befehle!\n\n**Mögliche Befehle:**\n`open` - Lädt AI Studio\n`grid` - Zeigt 10x10 Raster\n`grid 20` - Zeigt 20x20 Raster\n`klick B4` - Klickt auf Koordinate\n`tippe Hallo` - Tippt Text ein\n`enter` - Drückt Return\n`upload` - Lädt aktuellen Screen in AI Studio hoch\n`lies` - Liest die AI Antwort aus\n`stop` - Beendet alles", 
        parse_mode='Markdown'
    )
    
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
        
        while True:
            cmd_raw = await cmd_queue.get()
            cmd_parts = cmd_raw.split(" ", 1)
            cmd = cmd_parts[0].lower()
            args = cmd_parts[1] if len(cmd_parts) > 1 else ""
            
            try:
                if cmd == "open":
                    await bot.send_message(chat_id=CHAT_ID, text="🔄 Lade AI Studio...")
                    await page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
                    await asyncio.sleep(5)
                    await send_screenshot(page, bot, "✅ Geladen.")
                    
                elif cmd == "grid":
                    size = 20 if "20" in args else 10
                    _current_grid_size = size
                    await send_screenshot(page, bot, f"📐 Grid {size}x{size}", grid_size=size)
                    
                elif cmd == "klick":
                    tile = args.strip().upper()
                    w, h = page.viewport_size['width'], page.viewport_size['height']
                    coords = get_coordinates_from_grid(tile, w, h, _current_grid_size)
                    if coords:
                        await page.mouse.click(coords[0], coords[1])
                        await asyncio.sleep(2)
                        await send_screenshot(page, bot, f"🖱️ Geklickt auf {tile}")
                    else:
                        await bot.send_message(chat_id=CHAT_ID, text="❌ Ungültige Kachel.")
                        
                elif cmd == "tippe":
                    await page.keyboard.type(args)
                    await send_screenshot(page, bot, f"⌨️ Getippt: {args}")
                    
                elif cmd == "enter":
                    await page.keyboard.press("Enter")
                    await asyncio.sleep(2)
                    await send_screenshot(page, bot, "⏎ Enter gedrückt")
                    
                elif cmd == "ctrl+enter" or cmd == "ctrlenter":
                    await page.keyboard.press("Control+Enter")
                    await bot.send_message(chat_id=CHAT_ID, text="🚀 Prompt gesendet! (Control+Enter)")
                    
                elif cmd == "warte":
                    sec = int(args) if args.isdigit() else 10
                    await bot.send_message(chat_id=CHAT_ID, text=f"⏳ Warte {sec} Sekunden...")
                    await asyncio.sleep(sec)
                    await send_screenshot(page, bot, f"✅ Warten beendet.")

                elif cmd == "upload":
                    path = "temp/screen_to_analyze.png"
                    await page.screenshot(path=path)
                    await bot.send_message(chat_id=CHAT_ID, text="⚙️ Führe Upload-Prozedur aus...")
                    try:
                        await page.locator('button[aria-label="Insert images, videos, audio, or files"]').click()
                        await asyncio.sleep(1)
                        await page.locator('input[type="file"]').set_input_files(path)
                        await asyncio.sleep(2)
                        await send_screenshot(page, bot, "📤 Bild ist im Upload-Feld!")
                    except Exception as e:
                        await bot.send_message(chat_id=CHAT_ID, text=f"❌ Upload fehlgeschlagen: {e}")
                    
                elif cmd == "lies":
                    await bot.send_message(chat_id=CHAT_ID, text="🔎 Scanne DOM nach Antworten...")
                    # Aggressive Extraktion des Texts
                    texts = await page.evaluate('''() => {
                        return Array.from(document.querySelectorAll('.model-response-text, .markdown-renderer, p, .chat-message'))
                            .map(e => e.innerText)
                            .filter(t => t && t.trim().length > 20);
                    }''')
                    
                    if texts:
                        last_text = texts[-1]
                        # Safe Markdown send
                        text_to_send = last_text[:3500].replace("```", "'''")
                        await bot.send_message(chat_id=CHAT_ID, text=f"🧠 **Gefundener Text:**\n\n```text\n{text_to_send}\n```", parse_mode='Markdown')
                    else:
                        await bot.send_message(chat_id=CHAT_ID, text="❌ Nichts gefunden. Versuche 'lies all'")
                        
                elif cmd == "lies all":
                    body_text = await page.locator('body').inner_text()
                    await bot.send_message(chat_id=CHAT_ID, text=f"📜 **Body-Dump (letzte 3000 Zeichen):**\n\n{body_text[-3000:]}")
                    
                elif cmd == "screenshot":
                    await send_screenshot(page, bot, "📸 Aktueller Viewport")

                elif cmd == "stop":
                    await bot.send_message(chat_id=CHAT_ID, text="🛑 Beende Session.")
                    break
                else:
                    await bot.send_message(chat_id=CHAT_ID, text=f"❓ Unbekannter Befehl. Nutze: open, grid, grid 20, klick, tippe, enter, ctrl+enter, upload, warte 15, lies, screenshot, stop")
                    
            except Exception as e:
                await bot.send_message(chat_id=CHAT_ID, text=f"💥 Fehler bei {cmd}: {e}")
                
        await context.close()

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("No Telegram Token or Chat ID")
        return
        
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_tg_message))
    
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    try:
        await browser_loop(app.bot)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())