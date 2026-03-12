import asyncio
import os
import sys
import logging
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Configure basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load Environment Variables (Tokens, Allowed Users)
# In production we would use python-dotenv. For this skeleton, we assume os.environ is populated or we load from a .env file.
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    logger.warning("python-dotenv not installed, assuming env variables are set.")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]

async def is_authorized(update: Update) -> bool:
    """Security check: Only allow messages from whitelisted user IDs."""
    if not update.effective_user:
        return False
    user_id = update.effective_user.id
    if not ALLOWED_IDS:
        logger.warning("No ALLOWED_TELEGRAM_USER_IDS set! The bot is completely locked down.")
        return False
    if user_id not in ALLOWED_IDS:
        logger.warning(f"Unauthorized access attempt from user ID: {user_id}")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    if not await is_authorized(update):
        return
    await context.bot.send_message(
        chat_id=update.effective_chat.id, 
        text="🚀 Orchestrator Bot Online! Ich höre auf deine Befehle."
    )

async def echo_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Simple echo handler for Phase 1 testing."""
    if not await is_authorized(update):
        return
    
    text = update.message.text
    if text.lower() == "ping":
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Pong!")
    else:
        await context.bot.send_message(
            chat_id=update.effective_chat.id, 
            text=f"Ich habe empfangen: {text}\n*(In Phase 2 wird dies an den Router geleitet)*"
        )

def main():
    if not TELEGRAM_TOKEN:
        print("❌ CRITICAL ERROR: TELEGRAM_BOT_TOKEN is not set in environment.")
        sys.exit(1)
        
    print(f"🔒 Bot Security: Allowed User IDs = {ALLOWED_IDS}")
    
    # Build application
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    # Add handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), echo_handler))
    
    print("🚀 Starting Telegram Bot polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
