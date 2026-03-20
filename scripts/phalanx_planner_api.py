import asyncio
import os
import sys
import logging
import json
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pydantic import BaseModel, Field
from google import genai
from google.genai import types

sys.path.append("/app")
from src.modules.browser.magic_link import get_user_click_via_magic_link
from src.modules.browser.grid_helper import draw_grid_on_image
from PIL import Image

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("PhalanxPlannerAPI")

TELEGRAM_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
ALLOWED_IDS_STR = os.getenv("ALLOWED_TELEGRAM_USER_IDS", "")
ALLOWED_IDS = [int(id_str.strip()) for id_str in ALLOWED_IDS_STR.split(",") if id_str.strip().isdigit()]
CHAT_ID = ALLOWED_IDS[0] if ALLOWED_IDS else None
PROFILE_PATH = "/app/browser_sessions/account_cassie"
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# Global state
browser_page = None
bot_app = None
current_goal = None
workflow_log = []
planner_history = []

class PlannerResponse(BaseModel):
    reasoning: str = Field(description="Kurze Erklärung der aktuellen Situation und der gewählten Aktion.")
    action: str = Field(description="Aktionstyp: 'click', 'hover', 'type', 'wait', 'done', 'error'")
    target_text: str = Field(default="", description="Exakter, sichtbarer Text des Elements zum Klicken/Hovern.")
    input_text: str = Field(default="", description="Text zum Eintippen (falls action='type').")
    status: str = Field(description="'continue', wenn das Ziel noch nicht erreicht ist. 'done', wenn fertig.")

def save_crop_for_workflow(image_path, x, y, label, action_mode):
    try:
        os.makedirs("temp/workflow", exist_ok=True)
        with Image.open(image_path) as img:
            left, top = max(0, x - 50), max(0, y - 50)
            right, bottom = min(img.width, x + 50), min(img.height, y + 50)
            crop_img = img.crop((left, top, right, bottom))
            crop_path = f"temp/workflow/step_{len(workflow_log)}_{action_mode}_{label}.png"
            crop_img.save(crop_path)
            
            workflow_log.append({
                "step": len(workflow_log),
                "action": action_mode,
                "label": label,
                "x": x,
                "y": y,
                "template_image": crop_path
            })
            with open("temp/workflow/workflow_log.json", "w") as f:
                json.dump(workflow_log, f, indent=4)
            return crop_path
    except Exception as e:
        logger.error(f"Konnte Crop nicht speichern: {e}")
        return None

async def send_screenshot(caption, buttons=None):
    path = "temp/phalanx_view.png"
    await browser_page.screenshot(path=path)
    markup = InlineKeyboardMarkup(buttons) if buttons else None
    with open(path, "rb") as f:
        await bot_app.bot.send_photo(chat_id=CHAT_ID, photo=f, caption=caption, reply_markup=markup, parse_mode='Markdown')

async def init_browser():
    global browser_page
    p = await async_playwright().start()
    args = ["--no-sandbox", "--disable-blink-features=AutomationControlled"]
    if not os.getenv("DISPLAY"): os.environ["DISPLAY"] = ":99"
    context = await p.chromium.launch_persistent_context(
        user_data_dir=PROFILE_PATH, headless=False, args=args, viewport={"width": 1280, "height": 800}
    )
    browser_page = context.pages[0] if context.pages else await context.new_page()

async def get_gemini_plan(goal, image_path):
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    # Historie formatieren
    hist_str = "\n".join([f"Schritt {i+1}: {h}" for i, h in enumerate(planner_history[-3:])])
    prompt = f"""
Du bist der Phalanx Vision Planner. Du steuerst einen Webbrowser über Playwright.
ZIEL DES USERS: {goal}
BISHERIGE SCHRITTE:
{hist_str if hist_str else "Noch keine."}

Analysiere das aktuelle Bildschirmfoto. Was müssen wir JETZT tun, um dem Ziel näher zu kommen?
Gib strukturiert zurück, welche Aktion auf welchem Element ausgeführt werden soll.
Wenn wir klicken sollen, gib den exakten sichtbaren Text im UI zurück, damit Playwright ihn per Locator finden kann.
Wenn das Ziel erreicht ist (z.B. Modell ist ausgewählt), setze status auf 'done'.
"""
    # Lade Bild hoch für die API
    with Image.open(image_path) as img:
        response = client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[prompt, img],
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=PlannerResponse,
                temperature=0.0
            ),
        )
    
    return PlannerResponse.model_validate_json(response.text)

async def execute_planner_loop(goal):
    global planner_history
    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🚀 **Starte echten API-basierten Vision-Loop!**\nZiel: `{goal}`", parse_mode='Markdown')
    
    # Screenshot nehmen
    state_img = "temp/current_state.png"
    await browser_page.screenshot(path=state_img)
    
    try:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text="🧠 API Anfrage an Gemini 2.5 Flash läuft...")
        plan = await asyncio.to_thread(get_gemini_plan, goal, state_img)
        
        await bot_app.bot.send_message(
            chat_id=CHAT_ID, 
            text=f"💡 **Reasoning:** {plan.reasoning}\n🎯 **Aktion:** `{plan.action}` | **Target:** `{plan.target_text}` | **Status:** `{plan.status}`",
            parse_mode='Markdown'
        )
        
        if plan.status == 'done':
            await send_screenshot("🎉 **Ziel erreicht!** Workflow erfolgreich abgeschlossen.")
            return

        planner_history.append(f"Aktion: {plan.action} auf '{plan.target_text}'")

        if plan.action in ['click', 'hover'] and plan.target_text:
            try:
                # Hole die Bounding Box des Elements, bevor wir klicken, um die Mitte für den Crop zu berechnen
                loc = browser_page.locator(f'text="{plan.target_text}"').first
                box = await loc.bounding_box()
                
                if not box:
                    raise Exception("Bounding box nicht gefunden (Element nicht sichtbar).")
                    
                center_x = int(box['x'] + box['width'] / 2)
                center_y = int(box['y'] + box['height'] / 2)
                
                # Vor dem Klick den "sauberen" Screenshot speichern
                clean_img = "temp/clean_state.png"
                await browser_page.screenshot(path=clean_img)
                
                if plan.action == 'click':
                    await loc.click(timeout=3000)
                    await asyncio.sleep(2)
                else:
                    await loc.hover(timeout=3000)
                    await asyncio.sleep(1)
                    
                # Template speichern
                save_crop_for_workflow(clean_img, center_x, center_y, plan.target_text.replace(" ", "_"), plan.action)
                
                buttons = [
                    [InlineKeyboardButton("🔄 Weiter (Nächster Schritt)", callback_data='auto_continue')],
                    [InlineKeyboardButton("🛑 Stop", callback_data='abort')]
                ]
                await send_screenshot(f"✅ Aktion erfolgreich! Template gespeichert.", buttons)
                
            except Exception as e:
                logger.error(f"Playwright Fehler: {e}")
                buttons = [
                    [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click'), InlineKeyboardButton("✨ Magic Hover", callback_data='magic_hover')],
                    [InlineKeyboardButton("🛑 Abbrechen", callback_data='abort')]
                ]
                await send_screenshot(f"❌ Playwright konnte '{plan.target_text}' nicht klicken/hovern.\nFehler: {str(e)[:100]}\n\nBitte übernimm die Kontrolle mit Magic Link!", buttons)
        
        elif plan.action == 'type' and plan.input_text:
            await browser_page.keyboard.type(plan.input_text)
            await asyncio.sleep(1)
            buttons = [[InlineKeyboardButton("🔄 Weiter", callback_data='auto_continue')]]
            await send_screenshot(f"✅ Text getippt.", buttons)
            
        else:
            buttons = [
                [InlineKeyboardButton("🔄 Erneut versuchen", callback_data='auto_continue')],
                [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click')],
                [InlineKeyboardButton("🛑 Abbrechen", callback_data='abort')]
            ]
            await send_screenshot("⚠️ Aktion unklar oder nicht unterstützt.", buttons)

    except Exception as e:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"💥 Schwerer Fehler in API Loop: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_goal, planner_history, workflow_log
    if update.effective_user.id not in ALLOWED_IDS: return
    text = update.message.text.strip()
    
    if text.lower() == "open aistudio":
        await update.message.reply_text("🔄 Öffne AI Studio...", parse_mode='Markdown')
        await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await asyncio.sleep(5)
        buttons = [[InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click')]]
        await send_screenshot("✅ AI Studio geladen. Was ist das Ziel?", buttons)
    else:
        current_goal = text
        planner_history = []  # Reset History für neues Ziel
        workflow_log = []     # Reset Workflow Log
        await execute_planner_loop(current_goal)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_goal
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    decision = query.data
    
    if decision == 'auto_continue':
        await query.edit_message_caption(caption="🔄 Analysiere neuen Screen...")
        await execute_planner_loop(current_goal)
        
    elif decision in ['magic_click', 'magic_hover']:
        action_verb = "klicken" if decision == 'magic_click' else "hovern"
        await query.edit_message_caption(caption=f"🪄 Generiere Magic Link zum {action_verb}...")
        
        path = "temp/magic_view.png"
        await browser_page.screenshot(path=path)
        
        coords = await get_user_click_via_magic_link(path, bot_app, CHAT_ID, action_verb)
        
        if coords:
            x, y = coords
            action = 'click' if decision == 'magic_click' else 'hover'
            
            clean_bg = "temp/pre_action_clean.png"
            await browser_page.screenshot(path=clean_bg)
            save_crop_for_workflow(clean_bg, x, y, f"magic_{x}_{y}", action)
            
            if action == 'click':
                await browser_page.mouse.click(x, y)
                await asyncio.sleep(2)
            else:
                await browser_page.mouse.move(x, y)
                await asyncio.sleep(1)
                
            planner_history.append(f"Menschlicher {action} auf X:{x}, Y:{y} ausgeführt.")
            
            buttons = [
                [InlineKeyboardButton("🔄 KI Loop fortsetzen", callback_data='auto_continue')],
                [InlineKeyboardButton("✨ Weiterer Magic Klick", callback_data='magic_click')],
                [InlineKeyboardButton("🛑 Beenden", callback_data='abort')]
            ]
            await send_screenshot(f"✅ Magic {action} bei X:{x}, Y:{y} ausgeführt und Template gespeichert.\nWie weiter?", buttons)
        else:
            await bot_app.bot.send_message(chat_id=CHAT_ID, text="❌ Magic Link fehlgeschlagen.")
            
    elif decision == 'abort':
        await query.edit_message_caption(caption="🛑 Workflow beendet. JSON liegt in `temp/workflow/`.")
        current_goal = None

async def main():
    global bot_app
    if not TELEGRAM_TOKEN or not CHAT_ID or not GEMINI_API_KEY:
        logger.error("Token, Chat ID oder GEMINI_API_KEY fehlt.")
        return
        
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    await init_browser()
    
    await bot_app.bot.send_message(
        chat_id=CHAT_ID, 
        text="🚀 **Phalanx Vision Planner (True API Mode) Online!**\n\n1️⃣ Schreibe `open aistudio`\n2️⃣ Schreibe dein Ziel.\nDas System nutzt direkt die Gemini 2.0 API (Pydantic JSON), führt Playwright aus und speichert den Workflow für den CV-Bot!",
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