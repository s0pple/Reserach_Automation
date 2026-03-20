import asyncio
import os
import sys
import logging
import json
import time
from playwright.async_api import async_playwright
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, MessageHandler, CallbackQueryHandler, filters, ContextTypes
from pydantic import BaseModel, Field
from google import genai
from google.genai import types
from PIL import Image

sys.path.append("/app")
from src.modules.browser.magic_link import get_user_click_via_magic_link

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ApiCrucible")

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
    reasoning: str = Field(description="Warum wir das tun.")
    action: str = Field(description="Aktionstyp: 'click', 'type', 'wait', 'done', 'error'")
    target_text: str = Field(default="", description="Text des Elements zum Klicken.")
    input_text: str = Field(default="", description="Text zum Eintippen (falls action='type').")
    status: str = Field(description="'continue' oder 'done'.")

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
    path = "temp/api_view.png"
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
    if not GEMINI_API_KEY:
        raise Exception("Kein GEMINI_API_KEY gefunden!")
        
    client = genai.Client(api_key=GEMINI_API_KEY)
    
    hist_str = "\n".join([f"- {h}" for h in planner_history[-5:]])
    
    prompt = f"""
Du bist ein UI-Automatisierungs-Agent. Steuere den Browser, um das Ziel zu erreichen.
ZIEL: {goal}
HISTORIE:
{hist_str}

Analysiere den Screenshot. Was ist der nächste Schritt?
Antworte strikt im JSON Format.
- Wenn klicken: action='click', target_text='<Exakter Text im UI>'.
- Wenn tippen: action='type', input_text='<Text>'.
- Wenn fertig: action='done', status='done'.
"""
    try:
        with Image.open(image_path) as img:
            response = client.models.generate_content(
                model='gemini-2.0-flash', # Stabiles Modell
                contents=[prompt, img],
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=PlannerResponse,
                    temperature=0.0
                ),
            )
        return PlannerResponse.model_validate_json(response.text)
    except Exception as e:
        logger.error(f"Gemini API Error: {e}")
        return PlannerResponse(reasoning=f"API Error: {e}", action="error", status="continue")

async def execute_planner_loop(goal):
    global planner_history
    await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"🚀 **API Crucible Loop gestartet**\nZiel: `{goal}`", parse_mode='Markdown')
    
    state_img = "temp/current_state.png"
    await browser_page.screenshot(path=state_img)
    
    try:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text="🧠 API Anfrage an Gemini 2.0 Flash...")
        plan = await asyncio.to_thread(get_gemini_plan, goal, state_img)
        
        await bot_app.bot.send_message(
            chat_id=CHAT_ID, 
            text=f"💡 **Plan:** {plan.reasoning}\n👉 **Aktion:** `{plan.action}` on `{plan.target_text}`"
        )
        
        if plan.status == 'done':
            await send_screenshot("🎉 Ziel erreicht!")
            return

        planner_history.append(f"{plan.action} -> {plan.target_text}")

        if plan.action == 'click' and plan.target_text:
            try:
                # Locator finden
                loc = browser_page.locator(f'text="{plan.target_text}"').first
                # Wenn nicht gefunden, versuche unscharf
                if await loc.count() == 0:
                    loc = browser_page.locator(f'text={plan.target_text}').first
                
                box = await loc.bounding_box()
                if not box: raise Exception("Element nicht sichtbar/gefunden.")
                
                # Center berechnen
                cx = int(box['x'] + box['width'] / 2)
                cy = int(box['y'] + box['height'] / 2)
                
                # Clean Screenshot für Template
                clean_img = "temp/clean.png"
                await browser_page.screenshot(path=clean_img)
                save_crop_for_workflow(clean_img, cx, cy, f"auto_{plan.target_text}", "click")
                
                await loc.click(timeout=3000)
                await asyncio.sleep(2)
                
                buttons = [
                    [InlineKeyboardButton("🔄 Weiter", callback_data='continue')],
                    [InlineKeyboardButton("🛑 Stop", callback_data='abort')]
                ]
                await send_screenshot("✅ Klick ausgeführt.", buttons)
                
            except Exception as e:
                buttons = [
                    [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click')],
                    [InlineKeyboardButton("🛑 Abbrechen", callback_data='abort')]
                ]
                await send_screenshot(f"❌ Klick gescheitert: {e}\nBitte manuell eingreifen!", buttons)
                
        elif plan.action == 'type':
            await browser_page.keyboard.type(plan.input_text)
            await browser_page.keyboard.press("Enter")
            await asyncio.sleep(2)
            buttons = [[InlineKeyboardButton("🔄 Weiter", callback_data='continue')]]
            await send_screenshot(f"✅ Getippt: {plan.input_text}", buttons)
            
        else:
            # Fallback
            buttons = [
                [InlineKeyboardButton("✨ Magic Klick", callback_data='magic_click')],
                [InlineKeyboardButton("🔄 Retry", callback_data='continue')]
            ]
            await send_screenshot(f"⚠️ Aktion '{plan.action}' unklar.", buttons)

    except Exception as e:
        await bot_app.bot.send_message(chat_id=CHAT_ID, text=f"💥 Loop Error: {e}")

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global current_goal, planner_history, workflow_log
    if update.effective_user.id not in ALLOWED_IDS: return
    text = update.message.text.strip()
    
    if text.lower() == "open":
        await update.message.reply_text("🔄 Öffne AI Studio...")
        await browser_page.goto("https://aistudio.google.com/app/prompts/new_chat", timeout=60000)
        await asyncio.sleep(5)
        # Banners
        try:
            banners = browser_page.locator('button:has-text("Stimme zu"), button:has-text("I agree"), button:has-text("Accept")')
            if await banners.count() > 0: await banners.first.click(force=True)
        except: pass
        await send_screenshot("✅ Ready. Nenne das Ziel!")
    else:
        current_goal = text
        planner_history = []
        workflow_log = []
        await execute_planner_loop(current_goal)

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    if update.effective_user.id not in ALLOWED_IDS: return
    await query.answer()
    
    if query.data == 'continue':
        await query.edit_message_caption(caption="🔄 Loop läuft weiter...")
        await execute_planner_loop(current_goal)
        
    elif query.data == 'magic_click':
        await query.edit_message_caption(caption="🪄 Magic Link generieren...")
        path = "temp/magic.png"
        await browser_page.screenshot(path=path)
        coords = await get_user_click_via_magic_link(path, bot_app, CHAT_ID, "klicken")
        if coords:
            x, y = coords
            clean = "temp/clean_magic.png"
            await browser_page.screenshot(path=clean)
            save_crop_for_workflow(clean, x, y, f"magic_{x}_{y}", "click")
            
            await browser_page.mouse.click(x, y)
            await asyncio.sleep(2)
            
            planner_history.append(f"Manual Click at {x},{y}")
            
            buttons = [[InlineKeyboardButton("🔄 Weiter im Loop", callback_data='continue')]]
            await send_screenshot("✅ Manuell geklickt & gelernt.", buttons)
            
    elif query.data == 'abort':
        await query.edit_message_caption(caption="🛑 Beendet.")

async def main():
    global bot_app
    if not TELEGRAM_TOKEN: return
    bot_app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    bot_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    bot_app.add_handler(CallbackQueryHandler(handle_callback))
    
    await init_browser()
    await bot_app.bot.send_message(chat_id=CHAT_ID, text="🔥 **API Crucible Online**\nGemini 2.0 Flash Vision Loop.\nSchreibe `open`.")
    
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