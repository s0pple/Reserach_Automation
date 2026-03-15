import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    os.environ['DISPLAY'] = ':99'
    print("Starte Browser...")
    async with async_playwright() as p:
        # Gleiche Args wie in provider.py für einen echten Test
        browser = await p.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-setuid-sandbox",
                "--start-maximized",
                "--window-size=1920,1080"
            ]
        )
        page = await browser.new_page()
        await page.goto('https://google.ch')
        print("Google ist offen! Warte 10 Minuten. DRÜCKE JETZT /watch IN TELEGRAM!")
        await asyncio.sleep(600)
        await browser.close()
        print("Browser geschlossen.")

if __name__ == '__main__':
    asyncio.run(main())
