import asyncio
import os
import sys
import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, ContextTypes

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("InterceptionTest")

# Load Environment Variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]

# --- GLOBAL STATE FOR INTERCEPTION ---
_user_decision = None
_decision_event = asyncio.Event()

async def wait_for_human_help(screenshot_path: str, error_context: str, bot_instance, chat_id: str) -> str:
    """
    Diese Funktion wird vom Conveyor Belt im Slow-Path aufgerufen, wenn alles scheitert.
    Sie friert den Workflow ein, bis der User in Telegram einen Button drückt.
    """
    global _user_decision
    _user_decision = None
    _decision_event.clear() # Event zurücksetzen

    # 1. Buttons definieren (Die Optionen für den Menschen)
    keyboard = [
        [InlineKeyboardButton("⏭️ Skip Step (Ignorieren)", callback_data='skip_step')],
        [InlineKeyboardButton("🖱️ Klick-Override (Koordinaten)", callback_data='override_click')],
        [InlineKeyboardButton("🛑 Session Abbrechen", callback_data='abort_session')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    # 2. Hilferuf & Screenshot senden
    caption = f"🚨 **Hilfe benötigt!**\n\n**Kontext:** {error_context}\nWas soll ich tun?"
    
    # Check if screenshot exists, if not create a tiny 1x1 dummy PNG for testing
    if not os.path.exists(screenshot_path):
        os.makedirs(os.path.dirname(screenshot_path), exist_ok=True)
        try:
            from PIL import Image
            img = Image.new('RGB', (100, 100), color = (73, 109, 137))
            img.save(screenshot_path)
        except ImportError:
            with open(screenshot_path, "wb") as f:
                f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\x0bIDAT\x08\xd7c\xfa\xff\xff?\x00\x05\xfe\x02\xfe\x0c\xcc\xcc\xcc\x00\x00\x00\x00IEND\xaeB`\x82')


    with open(screenshot_path, 'rb') as photo:
        await bot_instance.send_photo(
            chat_id=chat_id, 
            photo=photo, 
            caption=caption, 
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

    print("⏸️ Förderband pausiert. Warte auf Telegram-Input...")

    # 3. HIER FRIERT DER AKTUELLE TASK EIN, BIS _decision_event.set() GERUFEN WIRD
    await _decision_event.wait()

    print(f"▶️ Menschliche Entscheidung empfangen: {_user_decision}. Förderband läuft wieder an.")
    return _user_decision

# --- TELEGRAM CALLBACK HANDLER ---
async def human_decision_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    Dieser Handler fängt den Button-Klick in Telegram ab und weckt das Förderband wieder auf.
    """
    global _user_decision
    query = update.callback_query
    
    # Check authorization
    if update.effective_user.id not in ALLOWED_IDS:
        await query.answer("Unauthorized", show_alert=True)
        return

    await query.answer() # Signalisiert Telegram, dass Klick empfangen wurde

    # 1. Entscheidung speichern
    _user_decision = query.data

    # 2. Nachricht aktualisieren (damit man nicht doppelt klickt)
    await query.edit_message_caption(
        caption=f"✅ Entscheidung übernommen: `{_user_decision}`. Workflow läuft weiter.",
        parse_mode='Markdown'
    )

    # 3. DAS EVENT SETZEN -> Weckt die wait_for_human_help() Funktion auf!
    _decision_event.set()


# --- DUMMY CONVEYOR BELT (TEST WORKFLOW) ---
async def conveyor_belt_loop(bot_instance, chat_id: str):
    """
    Simuliert unseren Fast-Path Workflow, der nach ein paar Schritten crasht
    und den Interceptor ruft.
    """
    print("🏭 Conveyor Belt gestartet...")
    
    for step in range(1, 6):
        print(f"⚙️ Führe Schritt {step} aus...")
        await asyncio.sleep(2) # Simuliere Arbeit
        
        if step == 3:
            print("💥 CRASH in Schritt 3! Element nicht gefunden.")
            # Slow-Path Fallback -> Telegram Interception
            screenshot_path = "temp/dummy_crash.png"
            
            decision = await wait_for_human_help(
                screenshot_path=screenshot_path,
                error_context="Konnte das 'Gemini 3.1 Pro' Dropdown nicht finden.",
                bot_instance=bot_instance,
                chat_id=chat_id
            )
            
            if decision == 'abort_session':
                print("🛑 Session durch User abgebrochen!")
                break
            elif decision == 'skip_step':
                print("⏭️ Überspringe Fehler und mache weiter...")
            elif decision == 'override_click':
                print("🖱️ Führe manuellen Klick-Override aus...")
                
        print(f"✅ Schritt {step} abgeschlossen.\n")
        
    print("🏁 Conveyor Belt beendet.")
    # Stop the program after test
    os._exit(0)


async def main():
    if not TELEGRAM_TOKEN:
        logger.error("No TELEGRAM_BOT_TOKEN provided.")
        sys.exit(1)
        
    if not ALLOWED_IDS:
        logger.error("No ALLOWED_TELEGRAM_USER_IDS provided.")
        sys.exit(1)

    chat_id = ALLOWED_IDS[0]

    # Initialize Bot Application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Register the callback handler for the buttons
    application.add_handler(CallbackQueryHandler(human_decision_handler))
    
    # Start the application in the background
    await application.initialize()
    await application.start()
    await application.updater.start_polling(drop_pending_updates=True)
    
    print("🚀 Telegram Interceptor Bot Online.")
    
    # Start the Conveyor Belt test loop concurrently
    try:
        await conveyor_belt_loop(application.bot, str(chat_id))
    finally:
        await application.updater.stop()
        await application.stop()
        await application.shutdown()

if __name__ == "__main__":
    asyncio.run(main())