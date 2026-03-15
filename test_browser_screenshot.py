import asyncio
import os
import subprocess
from playwright.async_api import async_playwright

async def main():
    os.environ['DISPLAY'] = ':99'
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()
        await page.goto('https://example.com')
        # Wait a bit to ensure rendering
        await asyncio.sleep(2)
        
        # Take screenshot of the entire X display
        subprocess.run(['scrot', 'xvfb_screenshot.png'])
        
        # Also take playwright screenshot for comparison
        await page.screenshot(path='playwright_screenshot.png')
        
        await browser.close()

if __name__ == '__main__':
    asyncio.run(main())
