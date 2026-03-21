# -*- coding: utf-8 -*-
import asyncio
from playwright.async_api import async_playwright
from src.core.browser_manager import BrowserManager

async def manual_login():
    print("Starte VNC Session fuer manuellen Login...")
    async with async_playwright() as p:
        browser_manager = BrowserManager(p, headless=False)
        context_path = "/app/data/browser_sessions/account_baldyboy"
        context = await browser_manager.start_context(context_path)
        page = context.pages[0] if context.pages else await context.new_page()
        
        await page.goto("https://aistudio.google.com/app/prompts/new_chat")
        
        print("\n=======================================================")
        print("BITTE JETZT IM VNC VIEWER EINLOGGEN!")
        print("Du hast 3 Minuten Zeit...")
        print("=======================================================\n")
        
        for i in range(180):
            if i % 10 == 0:
                print(f"Noch {180 - i} Sekunden...")
            await page.wait_for_timeout(1000)
            
        print("Schliesse Session...")
        await browser_manager.close()

if __name__ == '__main__':
    asyncio.run(manual_login())
