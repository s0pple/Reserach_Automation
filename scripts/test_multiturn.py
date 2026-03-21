import asyncio
from playwright.async_api import async_playwright
from src.core.browser_manager import BrowserManager
from src.core.ai_studio_controller import AIStudioController

async def test_multiturn():
    print("Starte Multiturn Test (Continuous Session) in AI Studio...")
    async with async_playwright() as p:
        browser_manager = BrowserManager(p, headless=False)
        context = await browser_manager.start_context()
        page = context.pages[0] if context.pages else await context.new_page()
        
        try:
            controller = AIStudioController(page)
            print("1. Initialisiere Session...")
            await controller.init_session()
            print("2. Setze Modell auf Gemini 3.1 Pro Preview...")
            await controller.set_model("Gemini 3.1 Pro Preview")
            
            prompt_1 = "Was ist 5 plus 5? Antworte kurz."
            print(f"\n--- RUNDE 1 ---\nSende Frage: {prompt_1}")
            await controller.send_prompt(prompt_1)
            response_1 = await controller.wait_for_response()
            print(f"Antwort 1: {response_1.strip()}")
            
            prompt_2 = "Und was ist dieses Ergebnis mal 2?"
            print(f"\n--- RUNDE 2 ---\nSende Frage: {prompt_2}")
            await controller.send_prompt(prompt_2)
            response_2 = await controller.wait_for_response()
            print(f"Antwort 2: {response_2.strip()}")

            prompt_3 = "Fasse unsere bisherige kleine Rechnung zusammen."
            print(f"\n--- RUNDE 3 ---\nSende Frage: {prompt_3}")
            await controller.send_prompt(prompt_3)
            response_3 = await controller.wait_for_response()
            print(f"Antwort 3: {response_3.strip()}")
            
            print("\n=== MULTITURN TEST ERFOLGREICH ===")
        except Exception as e:
            print(f"Fehler: {e}")
            await controller.magic_touch_pause(10, str(e))
        finally:
            await browser_manager.close()

if __name__ == '__main__':
    asyncio.run(test_multiturn())
