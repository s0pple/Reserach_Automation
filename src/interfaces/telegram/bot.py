import asyncio
import os
import sys
import logging
from telegram import Update, InputMediaPhoto
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes

# Project Imports
from src.agents.local_router.router import analyze_intent
from src.tools.web.qwen_researcher import register as register_qwen, qwen_research_tool
from src.tools.general.agent_tool import register as register_general, general_agent_tool

# Register all tools once
register_qwen()
register_general()

# Configure basic logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Load Environment Variables
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]

async def is_authorized(update: Update) -> bool:
    """Rule 1: Whitelist Security Check"""
    if not update.effective_user:
        return False
    user_id = update.effective_user.id
    if user_id not in ALLOWED_IDS:
        logger.warning(f"🔒 Unauthorized access attempt from user ID: {user_id}")
        return False
    return True

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for the /start command."""
    if not await is_authorized(update):
        return
    welcome_text = (
        "🚀 *Orchestrator Bot Online! (Phase 2)*\n\n"
        "Ich bin deine Fernsteuerung für den God-Container.\n"
        "Schicke mir einfach ein Thema, z.B.:\n"
        "`Zukunft der Solarenergie 2030`"
    )
    await context.bot.send_message(chat_id=update.effective_chat.id, text=welcome_text, parse_mode='Markdown')

import time

async def watch(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rule 1 & 2: Asynchroner Watchtower (Live-Screenshot)"""
    if not await is_authorized(update):
        return
        
    chat_id = update.effective_chat.id
    status_msg = await context.bot.send_message(chat_id=chat_id, text="📸 *Hole Live-Bild vom God-Container (:99)...*", parse_mode='Markdown')
    
    timestamp = int(time.time())
    filepath = f"temp/watchtower_{timestamp}.png"
    
    try:
        os.makedirs("temp", exist_ok=True)
        
        # Asynchroner Screenshot via scrot (non-blocking)
        env = os.environ.copy()
        env["DISPLAY"] = ":99"
        
        process = await asyncio.create_subprocess_exec(
            'scrot', filepath,
            env=env,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        if process.returncode == 0 and os.path.exists(filepath):
            with open(filepath, 'rb') as photo:
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=photo,
                    caption="👁️ *The Watchtower:* Live-Ansicht aus dem Xvfb-Monitor.",
                    parse_mode='Markdown'
                )
            await context.bot.delete_message(chat_id=chat_id, message_id=status_msg.message_id)
        else:
            error_msg = stderr.decode() if stderr else "Unbekannter Fehler"
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"❌ *Screenshot fehlgeschlagen:* {error_msg}",
                parse_mode='Markdown'
            )
            
    except Exception as e:
        logger.error(f"Watchtower Error: {e}")
        await context.bot.edit_message_text(
            chat_id=chat_id,
            message_id=status_msg.message_id,
            text=f"💥 *Systemfehler (Watchtower):* {str(e)}",
            parse_mode='Markdown'
        )
    finally:
        # Cleanup
        if os.path.exists(filepath):
            try:
                os.remove(filepath)
            except:
                pass

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Rule 2 & 3: Live-Feedback & Async-Safety"""
    if not await is_authorized(update):
        return
    
    user_query = update.message.text
    chat_id = update.effective_chat.id
    
    # Send Heartbeat 1
    status_msg = await context.bot.send_message(chat_id=chat_id, text="🧠 *Router analysiert Intent...*", parse_mode='Markdown')
    
    try:
        # 1. Router fragt lokales Modell (Qwen2.5)
        intent = await analyze_intent(user_query)
        tool_name = intent.get("tool", "qwen_research")
        params = intent.get("parameters", {"topic": user_query})
        
        logger.info(f"Router decided: {tool_name} with params: {params}")
        
        # Send Heartbeat 2
        await context.bot.edit_message_text(
            chat_id=chat_id, 
            message_id=status_msg.message_id, 
            text=f"✅ *Intent erkannt:* `{tool_name}`\n🔍 Starte Recherche zu: _{params.get('topic', user_query)}_...", 
            parse_mode='Markdown'
        )
        
        # 2. Tool Execution (Rule 3: Async & Non-Blocking)
        if tool_name == "qwen_research":
            # Extract topic from params
            topic = params.get("topic", user_query)
            
            # Execute tool directly via registered function or tool wrapper
            result = await qwen_research_tool(topic=topic, wait_minutes=2)
            
            if result.get("success"):
                report_content = result.get("content", "")
                report_len = result.get("length", 0)
                
                # Send Heartbeat 3
                await context.bot.edit_message_text(
                    chat_id=chat_id, 
                    message_id=status_msg.message_id, 
                    text=f"🎉 *Research abgeschlossen!* ({report_len} Zeichen)\n📦 Bereite Dokument vor...", 
                    parse_mode='Markdown'
                )
                
                # Save to temp file and send
                temp_file = f"temp/telegram_report_{chat_id}.md"
                os.makedirs("temp", exist_ok=True)
                with open(temp_file, "w", encoding="utf-8") as f:
                    f.write(report_content)
                
                await context.bot.send_document(
                    chat_id=chat_id, 
                    document=open(temp_file, 'rb'), 
                    filename=f"Research_{topic.replace(' ', '_')[:20]}.md",
                    caption=f"Hier ist dein Deep Research Bericht zu: {topic}"
                )
            else:
                await context.bot.send_message(chat_id=chat_id, text=f"❌ *Fehler im Researcher:* {result.get('error')}", parse_mode='Markdown')
                
        elif tool_name == "general_agent":
            goal = params.get("goal", user_query)

            # Heartbeat specific for general agent
            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=f"🧠 *General Agent übernimmt:* `{goal}`\n⚙️ Initiiere ReAct-Loop (Planning)...",
                parse_mode='Markdown'
            )

            async def status_updater(msg_text: str):
                try:
                    await context.bot.edit_message_text(
                        chat_id=chat_id,
                        message_id=status_msg.message_id,
                        text=f"🧠 *General Agent (Live-Status):*\n{msg_text}",
                        parse_mode='Markdown'
                    )
                except Exception as e:
                    logger.warning(f"Failed to update telegram message: {e}")

            result = await general_agent_tool(goal=goal, telegram_callback=status_updater)

            await context.bot.edit_message_text(
                chat_id=chat_id,
                message_id=status_msg.message_id,
                text=result.get("content"),
                parse_mode='Markdown'
            )
        else:
            await context.bot.send_message(chat_id=chat_id, text=f"🛠️ Das Tool `{tool_name}` ist in Phase 2 noch in Vorbereitung.", parse_mode='Markdown')

    except Exception as e:
        logger.error(f"Telegram Bot Error: {e}")
        await context.bot.send_message(chat_id=chat_id, text=f"💥 *Systemfehler:* {str(e)}")

active_streams = {}

async def stop_live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Stops an active live stream."""
    if not await is_authorized(update):
        return
    chat_id = update.effective_chat.id
    if chat_id in active_streams:
        active_streams[chat_id] = False
        await context.bot.send_message(chat_id=chat_id, text="🛑 *Live-Stream gestoppt.*", parse_mode='Markdown')
    else:
        await context.bot.send_message(chat_id=chat_id, text="Es läuft aktuell kein Stream.", parse_mode='Markdown')

async def live(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Starts a stop-motion live stream from Xvfb."""
    if not await is_authorized(update):
        return
    
    chat_id = update.effective_chat.id
    if active_streams.get(chat_id):
        await context.bot.send_message(chat_id=chat_id, text="⚠️ Es läuft bereits ein Stream. Nutze /stop zum Beenden.")
        return
        
    active_streams[chat_id] = True
    status_msg = await context.bot.send_message(chat_id=chat_id, text="🎥 *Starte Live-Stream...* (Nutze /stop zum Beenden)", parse_mode='Markdown')
    
    async def _stream_loop():
        stream_msg = None
        filepath = f"temp/live_{chat_id}.png"
        os.makedirs("temp", exist_ok=True)
        
        env = os.environ.copy()
        env["DISPLAY"] = ":99"
        
        try:
            while active_streams.get(chat_id):
                # Take screenshot
                process = await asyncio.create_subprocess_exec(
                    'scrot', filepath,
                    env=env,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE
                )
                await process.communicate()
                
                if process.returncode == 0 and os.path.exists(filepath):
                    try:
                        with open(filepath, 'rb') as photo:
                            if not stream_msg:
                                # Send initial photo
                                stream_msg = await context.bot.send_photo(
                                    chat_id=chat_id,
                                    photo=photo,
                                    caption="🔴 *LIVE* - God Container"
                                )
                            else:
                                # Update existing photo
                                await context.bot.edit_message_media(
                                    chat_id=chat_id,
                                    message_id=stream_msg.message_id,
                                    media=InputMediaPhoto(media=photo, caption="🔴 *LIVE* - God Container")
                                )
                    except Exception as stream_err:
                        # Ignore 'Message is not modified' error if the screen hasn't changed
                        if "Message is not modified" not in str(stream_err):
                            logger.error(f"Live Stream update error: {stream_err}")
                
                await asyncio.sleep(3) # Wait 3 seconds before next frame
                
        except Exception as e:
            logger.error(f"Live Stream Error: {e}")
        finally:
            active_streams[chat_id] = False
            if os.path.exists(filepath):
                try: os.remove(filepath)
                except: pass

    # Run stream loop in the background so it doesn't block other messages!
    asyncio.create_task(_stream_loop())


def main():
    if not TELEGRAM_TOKEN:
        print("❌ CRITICAL ERROR: TELEGRAM_BOT_TOKEN is not set.")
        sys.exit(1)
        
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('watch', watch))
    application.add_handler(CommandHandler('live', live))
    application.add_handler(CommandHandler('stop', stop_live))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_message))
    
    print("🚀 Starting Telegram Bot (Phase 2) polling...")
    application.run_polling()

if __name__ == '__main__':
    main()
