import asyncio
from playwright.async_api import async_playwright

async def get_coords():
    async with async_playwright() as p:
        context = await p.chromium.launch_persistent_context(
            user_data_dir="browser_sessions/account_cassie",
            headless=True,
            args=["--no-sandbox", "--disable-blink-features=AutomationControlled"]
        )
        page = context.pages[0] if context.pages else await context.new_page()
        await page.goto("https://aistudio.google.com/app/prompts/new_chat")
        await page.wait_for_load_state("networkidle")
        
        button = page.locator("button[aria-label='Run']")
        try:
            await button.wait_for(state="visible", timeout=5000)
            box = await button.bounding_box()
            if box:
                print(f"BOX: {box}")
            else:
                print("Button found but no bounding box.")
        except:
            print("Button not found.")
            
        await context.close()

if __name__ == "__main__":
    asyncio.run(get_coords())
