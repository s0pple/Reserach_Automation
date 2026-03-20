import asyncio
from playwright.async_api import async_playwright

async def dump_html():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="browser_sessions/account_cassie",
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://aistudio.google.com/app/prompts/new_chat")
        await page.wait_for_load_state("networkidle")
        
        # specific wait to ensure UI is loaded
        try:
            await page.wait_for_selector("textarea", timeout=10000)
        except:
            print("Textarea not found immediately, dumping anyway.")

        html = await page.content()
        with open("aistudio_dump.html", "w", encoding="utf-8") as f:
            f.write(html)
        print("Dumped HTML to aistudio_dump.html")
        
        await context.close()

if __name__ == "__main__":
    asyncio.run(dump_html())
