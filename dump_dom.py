import asyncio, sys
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        ctx = await p.chromium.launch_persistent_context(
            user_data_dir='/app/data/browser_sessions/acc_1',
            headless=False,
            slow_mo=0,
            args=['--no-sandbox','--disable-dev-shm-usage']
        )
        await asyncio.sleep(3)
        page = ctx.pages[0] if ctx.pages else await ctx.new_page()
        
        print(f'URL: {page.url}')
        print(f'Title: {await page.title()}')
        
        tags = await page.evaluate("""() => {
            const s = new Set();
            document.querySelectorAll('*').forEach(e => s.add(e.tagName.toLowerCase()));
            return [...s].filter(t => t.includes('-')).sort();
        }""")
        print(f'Custom tags ({len(tags)}): {tags[:30]}')
        
        for sel in ['.model-turn','model-turn','ms-text-chunk','ms-chat-turn',
                    '.message-content','message-content','chat-turn',
                    'ms-prompt-chunk','[class*=model]','p','h1','h2','h3','pre','code']:
            try:
                n = await page.locator(sel).count()
                if n > 0:
                    txt = await page.locator(sel).last.inner_text()
                    print(f'  FOUND [{n:3d}] {sel!r:40s} last_text[:80]={txt.strip()[:80]!r}')
                else:
                    print(f'  miss  [{n:3d}] {sel}')
            except Exception as e:
                print(f'  ERR        {sel}: {e}')
        
        await ctx.close()
        sys.stdout.flush()

asyncio.run(main())
