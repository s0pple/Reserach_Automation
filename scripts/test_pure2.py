import asyncio
from playwright.async_api import async_playwright

async def test_send():
    async with async_playwright() as p:
        b = await p.chromium.launch_persistent_context('/app/data/browser_sessions/account_baldyboy', headless=False, viewport={'width': 1280, 'height': 720})
        page = await b.new_page()
        print('Navigiere...')
        await page.goto('https://aistudio.google.com/app/prompts/new_chat', wait_until='networkidle')
        await page.wait_for_timeout(4000)
        
        print('Fokus und Eingabe...')
        box = page.locator('textarea').last
        await box.focus()
        
        # Sicherster Weg für Angular: press nacheinander
        await box.press_sequentially('Was ist 2+3?', delay=100)
        await page.wait_for_timeout(1000)
        
        print('Sende via JS-Click...')
        # Force JS click if disabled
        await page.locator('button.ctrl-enter-submits').evaluate('b => { b.disabled=false; b.click(); }')
        
        print('Oder via Locator press...')
        await box.press('Control+Enter')
        
        print('Warte 15s...')
        await page.wait_for_timeout(15000)
        
        mds = await page.locator('markdown-viewer').all()
        if mds:
             print('\n[RESULTAT]\n', await mds[-1].inner_text())
        else:
             print('Kein Markdown Viewer!')
             
        await page.screenshot(path='/app/temp/test_send_final.png')
        await b.close()

asyncio.run(test_send())
