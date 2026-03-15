import asyncio
import os
from playwright.async_api import async_playwright

async def main():
    os.environ['DISPLAY'] = ':99'
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=False,
            args=["--start-maximized", "--window-size=1920,1080"]
        )
        page = await browser.new_page()
        
        # Gehe zu einer Seite mit Bewegung/Veränderung
        await page.goto('https://time.is/Zurich')
        
        # Lass die Uhr für 1 Minute laufen (damit man im Stream sieht, wie die Sekunden ticken)
        for i in range(60):
            # scrolle etwas hin und her
            if i % 2 == 0:
                await page.evaluate("window.scrollBy(0, 200)")
            else:
                await page.evaluate("window.scrollBy(0, -200)")
            await asyncio.sleep(1)
            
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
