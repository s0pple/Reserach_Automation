import asyncio
import os
import sys
import logging
import re
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("AIOrchestrator")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"

# Global state
browser_page = None
_pending_cli_command = None

async def init_ai_studio():
    global browser_page
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
    
    logger.info("🔄 Lade AI Studio...")
    await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
    await asyncio.sleep(5)
    
    # Banners wegklicken
    try:
        banners = browser_page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
        if await banners.count() > 0: await banners.first.click(force=True)
    except: pass
    logger.info("✅ AI Studio bereit als Brain!")

async def ask_ai_studio(prompt: str, image_path: str = None) -> str:
    global browser_page
    if not browser_page: return "Fehler: AI Studio ist nicht verbunden."
    
    try:
        if image_path and os.path.exists(image_path):
            await browser_page.locator('button[aria-label="Insert images, videos, audio, or files"]').click()
            await asyncio.sleep(1)
            file_input = browser_page.locator('input[type="file"]')
            await file_input.set_input_files(image_path)
            await asyncio.sleep(2)
            
        textarea = browser_page.locator('textarea, div[contenteditable="true"]').last
        await textarea.fill(prompt)
        await browser_page.keyboard.press("Control+Enter")
        
        # Warte auf Generierung
        await asyncio.sleep(15) 
        
        # Lese Antwort aus
        responses = await browser_page.locator('chat-message, .model-response-text, .markdown-renderer').all_inner_texts()
        last_response = ""
        for resp in reversed(responses):
            if resp.strip() and len(resp.strip()) > 50:
                last_response = resp.strip()
                break
                
        if not last_response:
            last_response = await browser_page.locator('body').inner_text()
            last_response = last_response[-1500:]
            
        return last_response
    except Exception as e:
        return f"Fehler bei AI Studio Kommunikation: {e}"

def extract_bash_commands(text: str) -> list:
    """Sucht nach ```bash ... ``` Blöcken in der Antwort."""
    commands = []
    matches = re.findall(r'```(?:bash|sh)\n(.*?)```', text, re.DOTALL)
    for match in matches:
        commands.append(match.strip())
    return commands

async def handle_telegram_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _pending_cli_command
    if update.effective_user.id not in ALLOWED_IDS: return
    
    user_text = update.message.text.strip()
    status_msg = await update.message.reply_text("🧠 **Leite an AI Studio Brain weiter...**\nDenke nach...", parse_mode='Markdown')
    
    # Prompt für AI Studio bauen
    system_prompt = f"Du bist der Orchestrator-Agent für das Phalanx-System. Der User fragt: '{user_text}'. Wenn du Kommandozeilen-Befehle vorschlägst, verpacke sie UNBEDINGT in ```bash ... ``` Blöcke. Antworte kurz und prägnant auf Deutsch."
    
    ai_response = await ask_ai_studio(system_prompt)
    
    bash_commands = extract_bash_commands(ai_response)
    
    # Antwort sicher zurück nach Telegram schicken
    safe_response = ai_response[:3500].replace("```", "'''") # Markdown-Crashes verhindern
    await status_msg.edit_text(f"🤖 **AI Studio:**\n\n{safe_response}")
    
    if bash_commands:
        _pending_cli_command = "\n".join(bash_commands)
        
        keyboard = [
            [InlineKeyboardButton("🚀 CLI Befehl Ausführen", callback_data='run_cli')],
            [InlineKeyboardButton("🛑 Verwerfen", callback_data='discard_cli')]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await context.bot.send_message(
            chat_id=CHAT_ID,
            text=f"⚙️ **CLI Kommandos gefunden:**\n\n```bash\n{_pending_cli_command}\n```\nSoll ich das im Terminal ausführen?",
            reply_markup=reply_markup,
            parse_mode='Markdown'
        )

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global _pending_cli_command
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    if query.data == 'run_cli' and _pending_cli_command:
        await query.edit_message_text(f"🚀 Führe aus:\n```bash\n{_pending_cli_command}\n```", parse_mode='Markdown')
        
        # Führe Befehl im echten Terminal aus!
        process = await asyncio.create_subprocess_shell(
            _pending_cli_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await process.communicate()
        
        out_text = stdout.decode() if stdout else ""
        err_text = stderr.decode() if stderr else ""
        
        result_text = f"✅ **Ergebnis (Exit {process.returncode}):**\n"
        if out_text: result_text += f"\n*Output:*\n```text\n{out_text[:1000]}\n```"
        if err_text: result_text += f"\n*Error:*\n```text\n{err_text[:1000]}\n```"
        
        await context.bot.send_message(chat_id=CHAT_ID, text=result_text, parse_mode='Markdown')
        _pending_cli_command = None
        
    elif query.data == 'discard_cli':
        await query.edit_message_text("🗑️ Befehl verworfen.")
        _pending_cli_command = None

async def main():
    if not TELEGRAM_TOKEN or not CHAT_ID:
        logger.error("Telegram Config fehlt.")
        return
        
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_telegram_message))
    app.add_handler(CallbackQueryHandler(handle_callback))
    
    # 1. Starte Browser im Hintergrund
    await init_ai_studio()
    
    # 2. Sag Telegram Bescheid
    await app.bot.send_message(chat_id=CHAT_ID, text="🚀 **AI Orchestrator Online!**\nAI Studio ist geladen. Schreib mir einfach was du tun willst. Ich frage das Brain und generiere CLI-Befehle für dich!")
    
    # 3. Starte Polling
    await app.initialize()
    await app.start()
    await app.updater.start_polling(drop_pending_updates=True)
    
    logger.info("Bot lauscht auf Nachrichten...")
    
    # Halte Script am Leben
    try:
        while True:
            await asyncio.sleep(3600)
    finally:
        await app.updater.stop()
        await app.stop()
        await app.shutdown()

if __name__ == "__main__":
    asyncio.run(main())