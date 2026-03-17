import asyncio
import os
import sys
import logging
import time
import subprocess
import html
from telegram import Update
from telegram.ext import ApplicationBuilder, MessageHandler, filters, ContextTypes, CommandHandler

# Core/Registry
from src.core.registry import ToolRegistry
from src.schema.tool_parameters import ResearchParams, CLIParams, ProjectParams, WatchParams, GeneralAgentParams, SessionParams

# Tools
from src.core.persistence import JobRegistry
from src.agents.local_router.router import analyze_intent
from src.tools.general.cli_tool import run_cli_command
from src.tools.general.project_tool import get_project_status
from src.tools.general.agent_tool import general_agent_tool
from src.tools.general.session_tool import interactive_session_tool
from src.tools.web.ai_studio_tool import ai_studio_controller, AIStudioParams
from src.tools.dev.developer_tool import developer_reasoning_tool, DeveloperArguments
from src.tools.web.gemini_web_nav_tool import gemini_web_nav_tool, WebNavArguments

# Configure basic logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO
)
logger = logging.getLogger("PhalanxBot")

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
    if not update.effective_user: return False
    if update.effective_user.id not in ALLOWED_IDS:
        logger.warning(f"🔒 Unauthorized access attempt: {update.effective_user.id}")
        return False
    return True

# --- Helper: Safe Markdown ---
def safe_markdown(text: str) -> str:
    """Escapes markdown but allows code blocks if they are well-formed (simple check)."""
    # For simplicity in this bot, we often just want raw text or simple code blocks.
    # If the text contains incomplete markdown entities, Telegram explodes.
    # Strategy: If it looks like code, keep it, otherwise escape critical chars if needed.
    # Actually, the safest bet for unpredictable output is to NOT use Markdown for the bulk, 
    # OR wrap everything in a code block if it looks technical.
    
    if "```" in text or "`" in text:
        # It already tries to be markdown. Let's hope it's valid.
        return text
    
    # Escape special chars for Markdown V1/V2 if we were being strict,
    # but here we just return text. The error usually comes from unclosed entities.
    return text

# --- Tool Callbacks ---
async def trigger_job(topic: str):
    registry = JobRegistry()
    job_id = f"job_{int(time.time())}"
    log_path = os.path.abspath(f"temp/jobs/{job_id}/output.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    registry.register_job(job_id, topic, "PENDING", log_path)
    subprocess.Popen([sys.executable, "src/core/job_launcher.py", job_id, topic], start_new_session=True)
    return {"content": f"🚀 Forschungs-Mission `{job_id}` für _{topic}_ gestartet."}

async def take_watch(job_id=None):
    display = ":99"
    if job_id:
        job = JobRegistry().get_job(job_id)
        if job and job.get("display"): display = job["display"]
    
    filepath = f"temp/watch_{int(time.time())}.png"
    os.makedirs("temp", exist_ok=True)
    env = os.environ.copy(); env["DISPLAY"] = display
    
    process = await asyncio.create_subprocess_exec("scrot", "-z", filepath, env=env)
    await process.communicate()
    
    if os.path.exists(filepath):
        return {"photo_path": filepath, "caption": f"👁️ Display `{display}`"}
    else:
        return {"content": f"❌ Screenshot von {display} fehlgeschlagen."}


# --- Command Handlers ---
async def cmd_cli(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    args = context.args
    if not args:
        await update.message.reply_text("💡 **Nutzung:** `/cli [Befehl]`\nBeispiel: `/cli ls -la` oder `/cli gemini-cli \"How to fix X?\"`", parse_mode="Markdown")
        return
    
    command = " ".join(args)
    status_msg = await update.message.reply_text(f"⏳ Starte: `{command}`...", parse_mode="Markdown")
    
    # Use interactive_session_tool to start a new tmux session
    async def callback(text):
        try:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text, parse_mode="Markdown")
        except:
            await context.bot.send_message(chat_id=update.effective_chat.id, text=text)

    result = await interactive_session_tool(action="start", command=command, telegram_callback=callback)
    
    await context.bot.edit_message_text(
        chat_id=update.effective_chat.id,
        message_id=status_msg.message_id,
        text=result.get("message", "Error") + (f"\n🆔 ID: `{result.get('session_id')}`" if "session_id" in result else ""),
        parse_mode="Markdown"
    )

async def cmd_sessions(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    result = await interactive_session_tool(action="list")
    await update.message.reply_text(result.get("content", "Keine Info."), parse_mode="Markdown")

async def cmd_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/in [session_id] [text] - Send input to a session."""
    if not await is_authorized(update): return
    args = context.args
    if len(args) < 2:
        await update.message.reply_text("💡 **Nutzung:** `/in [ID] [Text]`\nBeispiel: `/in cli_abc y`", parse_mode="Markdown")
        return
    
    session_id = args[0]
    input_text = " ".join(args[1:])
    result = await interactive_session_tool(action="input", session_id=session_id, input_text=input_text)
    await update.message.reply_text(result.get("message", "Error"), parse_mode="Markdown")

async def cmd_help(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = """
🚀 **Phalanx 3.0 Command Center**

**Direkte Befehle:**
/cli `[Befehl]` - Startet interaktive Session
/in `[ID] [Input]` - Sendet Text an Session
/sessions - Listet alle aktiven Sessions
/status - Zeigt Hintergrund-Forschungs-Jobs
/watch - Macht Screenshot vom Haupt-Display

**Natürliche Sprache:**
Schreibe einfach was du willst, der Router wählt das beste Tool.
- "Recherche zum Thema KI in der Logistik"
- "Was ist der Status vom Projekt?"
- "Öffne AI Studio und schreibe einen Blogpost"
- "Finde den Button 'Accept' im AI Studio"
"""
    await update.message.reply_text(help_text, parse_mode="Markdown")


# --- The Universal Handler ---
async def handle_universal(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_authorized(update): return
    user_query = update.message.text
    if not user_query: return
    
    # 1. Quick Overrides (Bypass LLM for clear commands)
    q_low = user_query.lower()
    if q_low == "/status" or q_low == "status":
        registry = JobRegistry()
        jobs = registry.get_active_jobs()
        if not jobs: await update.message.reply_text("📭 Keine aktiven Jobs.")
        else: await update.message.reply_text("📋 *Aktive Jobs:*\n\n" + "\n".join([f"🆔 `{j['job_id']}` | 🖥️ `{j.get('display') or '...'}` | 🔹 `{j['status']}`" for j in jobs]), parse_mode="Markdown")
        return

    # 2. LLM Intent Analysis
    status_msg = await update.message.reply_text("🧠 *Höre zu...*", parse_mode="Markdown")
    try:
        intent = await analyze_intent(user_query)
        tool_name = intent.get("tool", "error")
        thought = intent.get("thought", "Thinking...")
        params = intent.get("parameters", {})
        
        logger.info(f"LLM Intent: {tool_name} with params: {params}")
        
        # Display Reasoning
        await context.bot.edit_message_text(
            chat_id=update.effective_chat.id, 
            message_id=status_msg.message_id, 
            text=f"🤔 Reasoning:\n{thought}\n\n🛠️ Tool: {tool_name}"
            # No parse_mode used here to be safe
        )


        # Provide a general async callback for tools that need to push updates
        async def telegram_callback(msg_text):
            try:
                # Use HTML parse mode for safer rendering of random text than Markdown
                # OR just plain text if unsure.
                await context.bot.send_message(chat_id=update.effective_chat.id, text=msg_text) 
            except Exception as e:
                logger.error(f"Callback send error: {e}")

        # Inject callback into params if the tool supports it
        if tool_name in ["general_agent", "interactive_session_tool", "web_nav_tool", "developer_tool", "ai_studio_tool"]:
            params["telegram_callback"] = telegram_callback

        # --- DYNAMIC ROUTING ---
        tool_info = ToolRegistry.get_tool(tool_name)
        
        if not tool_info:
            await context.bot.edit_message_text(
                chat_id=update.effective_chat.id, 
                message_id=status_msg.message_id, 
                text=f"❌ Fehler: Router hat ein unbekanntes Tool gewählt `{tool_name}`"
            )
            return

        # Execute the tool
        result = await tool_info.func(**params)
        
        # Handle Output
        if result:
            # Special handling for Watch tool which returns a photo path
            if "photo_path" in result:
                await context.bot.delete_message(chat_id=update.effective_chat.id, message_id=status_msg.message_id)
                with open(result["photo_path"], "rb") as photo:
                    await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption=result.get("caption", ""))
                os.remove(result["photo_path"])
            else:
                # Standard text output
                output_text = result.get("content") or result.get("message") or result.get("stdout") or result.get("error") or str(result)
                
                # Sanitize output slightly to prevent markdown errors if we keep parse_mode
                # Better strategy: Try Markdown, fallback to Text if it fails
                try:
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id, 
                        message_id=status_msg.message_id, 
                        text=f"✅ Ergebnis:\n{output_text[:3500]}"
                        # No parse mode
                    )
                except Exception as md_error:
                    logger.warning(f"Markdown failed, falling back to plain text: {md_error}")
                    await context.bot.edit_message_text(
                        chat_id=update.effective_chat.id, 
                        message_id=status_msg.message_id, 
                        text=f"✅ Ergebnis:\n{output_text[:3500]}"
                        # No parse mode
                    )

    except Exception as e:
        logger.error(f"Universal Handler Error: {e}")
        # Fallback error message
        try:
             await context.bot.edit_message_text(chat_id=update.effective_chat.id, message_id=status_msg.message_id, text=f"💥 Fehler: {e}")
        except:
             # If edit fails (e.g. message deleted), send new
             await context.bot.send_message(chat_id=update.effective_chat.id, text=f"💥 Fehler: {e}")

def main():
    # Tool Registration (Critical for LLM Router!)
    ToolRegistry.register_tool("general_agent", "Autonomous web agent.", general_agent_tool, GeneralAgentParams)
    ToolRegistry.register_tool("project_status_tool", "Reads local project board and to-dos.", get_project_status, ProjectParams)
    ToolRegistry.register_tool("cli_tool", "Executes short shell commands.", run_cli_command, CLIParams)
    ToolRegistry.register_tool("watch_tool", "Takes a screenshot of display.", take_watch, WatchParams)
    ToolRegistry.register_tool("ai_studio_tool", "Controls Google AI Studio via headless browser.", ai_studio_controller, AIStudioParams)
    ToolRegistry.register_tool("developer_tool", "Reasoning agent that explores the repository and answers complex technical questions.", developer_reasoning_tool, DeveloperArguments)
    ToolRegistry.register_tool("web_nav_tool", "Autonomous web agent powered by Gemini Vision. Use for tasks like 'Buy X', 'Check price of Y'.", gemini_web_nav_tool, WebNavArguments)
    ToolRegistry.register_tool("deep_research", "Start a background research job.", trigger_job, ResearchParams)
    ToolRegistry.register_tool("interactive_session_tool", "Starts, sends input to, or kills a persistent, interactive CLI session (like running gemini-cli, npm init, etc). Use action=start with a command to begin. Use action=input with session_id and input_text to reply to a running session.", interactive_session_tool, SessionParams)

    if not TELEGRAM_TOKEN: sys.exit(1)
    application = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    
    application.add_handler(CommandHandler("start", lambda u, c: u.message.reply_text("🚀 Phalanx 3.0 Universal Intelligence Ready.")))
    application.add_handler(CommandHandler("help", cmd_help))
    application.add_handler(CommandHandler("cli", cmd_cli))
    application.add_handler(CommandHandler("sessions", cmd_sessions))
    application.add_handler(CommandHandler("in", cmd_input))
    application.add_handler(CommandHandler("status", lambda u, c: u.message.reply_text("Nutze Status im Chat oder /sessions.")))
    application.add_handler(MessageHandler(filters.TEXT & (~filters.COMMAND), handle_universal))
    
    print("🚀 Phalanx 3.0 Universal Intelligence (OpenClaw Architecture) Online...")
    application.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
