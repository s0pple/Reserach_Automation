
import asyncio
from playwright.async_api import async_playwright

async def final_test():
    async with async_playwright() as p:
        b = await p.chromium.launch_persistent_context('/app/data/browser_sessions/account_baldyboy', headless=False, viewport={'width': 1280, 'height': 720})
        page = await b.new_page()
        print('1. Navigieren')
        await page.goto('https://aistudio.google.com/app/prompts/new_chat', wait_until='networkidle')
        await page.wait_for_timeout(4000)

        print('2. Oeffne Model Dropdown')
        await page.mouse.click(1120, 130)
        await page.wait_for_timeout(1000)
        
        print('3. Waehle Flash')
        try:
            await page.locator('span').filter(has_text='Flash').first.click(timeout=3000)
        except Exception:
            print('Konnte Flash nicht spezifisch finden, behalte Modell bei.')
            await page.keyboard.press('Escape')
        await page.wait_for_timeout(1000)

        print('4. Tippe Prompt')
        input_box = page.locator('textarea').last
        await input_box.fill('Nenne mir 3 kurze Fakten ueber rote Pandas. (Bitte auf Deutsch, 3 kurze Punkte)')
        await page.wait_for_timeout(1000)
        
        print('5. Sende Message (Ctrl+Enter)')
        # Alternativ den Run-Button versuchen, oder Ctrl+Enter auf die textarea
        await input_box.press('Control+Enter')
        await page.wait_for_timeout(1000)
        await page.keyboard.press('Control+Enter')
        
        print('6. Warte 15s auf Antwort...')
        await page.wait_for_timeout(15000)
        
        print('7. Extrahiere Output')
        res = await page.locator('markdown-viewer').all()
        if res:
             print('\n[RESULTAT]\n', await res[-1].inner_text())
        else:
             print('\n[RESULTAT FEHLT] Kein Markdown Viewer gefunden!\n')

        await page.screenshot(path='/app/temp/flash_final.png')
        await b.close()

asyncio.run(final_test())
