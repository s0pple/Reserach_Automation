import asyncio
import os
import time
import sys
import logging
from typing import List, Optional, Dict, Any
from src.core.search import SearchProvider, SearchResult
from src.modules.browser.profile_manager import BrowserProfileManager

# Configure basic logging for better visibility in CLI
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    from playwright.async_api import async_playwright, Page, BrowserContext
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    async_playwright = None
    Page = Any
    BrowserContext = Any
    PLAYWRIGHT_AVAILABLE = False

class BrowserSearchProvider(SearchProvider):
    """
    Core Automation Provider for 'Deep Research' tools (Gemini / Perplexity).
    Supports multi-account personas to bypass limits and parallelize research.
    """
    def __init__(self, headless: bool = False, persona: str = "main"):
        self.headless = headless
        self.persona = persona
        self.profile_manager = BrowserProfileManager()
        # Use isolated profile path for each persona
        self.user_data_dir = self.profile_manager.get_profile_path(persona)

    async def search(self, query: str, max_results: int = 5) -> List[SearchResult]:
        """Standard search interface (fallback)."""
        return [SearchResult(title="Deep Research", url="browser://local", snippet="Results in report.")]

    async def search_and_scrape(self, query: str, max_results: int = 3) -> List[Dict[str, str]]:
        """
        Focused hunting: Uses Google API (if available) or DDGS, then Playwright for content.
        """
        print(f"[Browser] 🕵️ Hunting: '{query}'")
        
        target_urls = []
        api_key = os.getenv("GOOGLE_SEARCH_API_KEY")
        search_id = os.getenv("GOOGLE_SEARCH_CX")

        # 1. Try Official Google API first
        if api_key and search_id:
            try:
                from googleapiclient.discovery import build
                service = build("customsearch", "v1", developerKey=api_key)
                res = service.cse().list(q=query, cx=search_id, num=max_results).execute()
                if "items" in res:
                    target_urls = [item["link"] for item in res["items"]]
                    print(f"  [Google API] Found {len(target_urls)} URLs.")
            except Exception as e:
                print(f"  [Google API] ⚠️ Error: {e}")

        # 2. Fallback to DuckDuckGo if Google API failed or keys missing
        if not target_urls:
            try:
                from duckduckgo_search import DDGS
                with DDGS() as ddgs:
                    ddg_results = ddgs.text(query, max_results=max_results * 2)
                    for r in ddg_results:
                        url = r['href'].lower()
                        if any(x in url for x in [".ru", ".info", "support.google", "youtube.com"]): continue
                        target_urls.append(r['href'])
                    target_urls = target_urls[:max_results]
                    print(f"  [DDGS Fallback] Found {len(target_urls)} URLs.")
            except Exception as e:
                print(f"  [Browser] ⚠️ Search fallback error: {e}")

        if not target_urls: return []

        # 3. Scrape with Playwright
        results = []
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context(locale="en-US")
            for url in target_urls:
                print(f"  [Scraping] {url}...")
                page = await context.new_page()
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    content = await page.evaluate("""
                        () => {
                            const main = document.querySelector('main, article, #content, .post-body');
                            return main ? main.innerText : document.body.innerText;
                        }
                    """)
                    results.append({"url": url, "text": content[:10000]})
                except Exception as e:
                    print(f"    [SKIP] {url}: {str(e)[:30]}")
                finally:
                    await page.close()
            await browser.close()
        return results

    async def trigger_deep_research(self, prompt: str, tool: str = "gemini") -> str:
        """
        Main entry point for real browser automation.
        """
        if not PLAYWRIGHT_AVAILABLE:
            print("\n[Browser] ❌ FATAL ERROR: Playwright not installed. Run 'pip install playwright'.")
            sys.exit(1)

        print(f"\n[Browser] 🚀 Launching Chrome | Persona: '{self.persona.upper()}' | Headless: {self.headless}")

        async with async_playwright() as p:
            context = None
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    viewport={'width': 1280, 'height': 800},
                    permissions=['clipboard-read', 'clipboard-write'],
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--start-maximized",
                        "--window-size=1920,1080"
                    ]
                )

                page = context.pages[0] if context.pages else await context.new_page()
                page.set_default_timeout(45000)

                if tool.lower() == "gemini":
                    return await self._run_gemini_deep_research(page, prompt)
                else:
                    return f"Unsupported tool: {tool}"

            except Exception as e:
                print(f"[Browser] ❌ CRITICAL ERROR in '{self.persona}': {str(e)}")
                try:
                    debug_path = f"debug_failed_{self.persona}.png"
                    await page.screenshot(path=debug_path)
                    print(f"[Browser] 📸 Screenshot saved to {debug_path}")
                except: pass
                raise e
            finally:
                if context:
                    print(f"[Browser] 🔒 Closing session for persona '{self.persona}'...")
                    await asyncio.sleep(1)
                    await context.close()

    async def _run_gemini_deep_research(self, page: Page, prompt: str) -> str:
        """
        Automates Gemini (Web App) to trigger its long-form Deep Research mode.
        """
        print("[Browser] 🌐 Navigating to Gemini...")
        try:
            await page.goto("https://gemini.google.com/app", wait_until="load", timeout=90000)
            await asyncio.sleep(5)
        except Exception as e:
            print(f"[Browser] ⚠️ Navigation warning: {str(e)[:50]}... proceeding anyway.")

        # Auth Check
        if "accounts.google.com" in page.url:
            print(f"[Browser] 🔑 AUTH REQUIRED for persona '{self.persona}'.")
            if not self.headless:
                print("[Browser] ⏳ Waiting for manual login (max 5 min)...")
                await page.wait_for_url("https://gemini.google.com/app*", timeout=300000)
                print("[Browser] ✅ Login detected!")
            else:
                raise Exception("Authentication required. Run with headless=False once.")

        # 1. Activate Deep Research Mode
        print("[Browser] 🔍 Activating Deep Research mode...")
        found = False
        try:
            # Close notice
            close_notice = page.get_by_role("button", name="Schließen").first
            if await close_notice.is_visible(timeout=2000):
                await close_notice.click()
                await asyncio.sleep(1)

            # Click Tools
            tools_btn = page.locator('button:has-text("Tools")').first
            if await tools_btn.is_visible(timeout=5000):
                await tools_btn.click()
                await asyncio.sleep(2)
                
                # Select Deep Research
                deep_research_opt = page.get_by_text("Deep Research", exact=False).first
                if await deep_research_opt.is_visible(timeout=3000):
                    await deep_research_opt.click()
                    await asyncio.sleep(2)
                    found = True
            
            if not found:
                # Fallback to model switcher
                model_switcher = page.locator('button:has-text("Fast"), button:has-text("Schnell"), button:has-text("Flash")').first
                if await model_switcher.is_visible(timeout=3000):
                    await model_switcher.click()
                    await asyncio.sleep(1)
                    deep_opt = page.get_by_text("Deep Research", exact=False).first
                    if await deep_opt.is_visible(timeout=2000):
                        await deep_opt.click()
                        found = True
        except Exception as e:
            print(f"[Browser] ⚠️ Mode activation error: {str(e)[:50]}")

        # 2. Enter Prompt
        print("[Browser] ✍️ Entering prompt (fast-fill)...")
        if page.is_closed(): return "Error: Browser closed."
        
        prompt_box = page.locator('div[contenteditable="true"], textarea').first
        await prompt_box.wait_for(state="visible", timeout=15000)
        await prompt_box.click()
        
        enriched_prompt = f"PERFORM DEEP RESEARCH ON: {prompt}. Provide a source-rich Markdown report."
        
        # Use evaluate to set the text instantly and as a single block
        await page.evaluate("""
            (args) => {
                const el = document.querySelector('div[contenteditable="true"], textarea');
                if (el.tagName === 'TEXTAREA') {
                    el.value = args.text;
                } else {
                    el.innerText = args.text;
                }
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }
        """, {"text": enriched_prompt})
        
        await asyncio.sleep(1)

        # 3. Submit
        print("[Browser] ⚡ Submitting via Send-Button...")
        send_btn = page.locator('button[aria-label*="Senden"], button[aria-label*="Send"]').first
        if await send_btn.is_visible():
            await send_btn.click()
        else:
            await page.keyboard.press("Enter")
        
        # 4. Confirmation Step (Wait for Plan to be generated)
        print("[Browser] ⏳ Waiting for Gemini to generate the research plan...")
        
        try:
            start_btn_found = False
            # Wait loop to aggressively find the start button (up to 60s)
            for attempt in range(30):
                if page.is_closed(): return "Error: Browser closed."
                
                # Continuously scroll to bottom as content generates
                await page.mouse.wheel(0, 2000)
                await page.keyboard.press("PageDown")
                
                # Check for different variants of the start button
                selectors = [
                    'button:has-text("Recherche starten")',
                    'button:has-text("Start research")',
                    'div[role="button"]:has-text("Recherche starten")',
                    'div[role="button"]:has-text("Start research")',
                    'span:has-text("Recherche starten")',
                    'span:has-text("Start research")',
                    'button:has-text("Starten")'
                ]
                
                for sel in selectors:
                    try:
                        btn = page.locator(sel).first
                        if await btn.is_visible(timeout=500):
                            print(f"[Browser] 🖱️ Found start button via '{sel}'!")
                            await btn.scroll_into_view_if_needed()
                            await asyncio.sleep(1)
                            await btn.click()
                            start_btn_found = True
                            break
                    except Exception:
                        pass
                
                if not start_btn_found:
                    try:
                        # Fallback using exact text matching
                        for text_match in ["Recherche starten", "Start research"]:
                            btn_text = page.get_by_text(text_match, exact=True).first
                            if await btn_text.is_visible(timeout=500):
                                print(f"[Browser] 🖱️ Found start button via text match ({text_match})!")
                                await btn_text.scroll_into_view_if_needed()
                                await asyncio.sleep(1)
                                await btn_text.click()
                                start_btn_found = True
                                break
                    except Exception:
                        pass
                
                if start_btn_found:
                    print("[Browser] ✅ Clicked Start Research successfully.")
                    await asyncio.sleep(5)
                    break
                
                await asyncio.sleep(2)
                if attempt > 0 and attempt % 5 == 0:
                    print(f"[Browser] ... still waiting for start button (attempt {attempt}/30) ...")

            if not start_btn_found:
                print("[Browser] ⚠️ Confirmation button not found after 60 seconds. Research might have started automatically.")
        except Exception as e:
            print(f"[Browser] ⚠️ Error during confirmation step: {str(e)[:100]}")

        # 5. Monitor Progress
        print("[Browser] ⏳ Deep Research in progress... (this will take several minutes)")
        
        # 1. Ziel definieren: Nur noch exakte Text-Matches, keine generischen Icons mehr!
        share_btn = page.locator('button:has-text("Teilen und exportieren"), button[aria-label*="Teilen"], button[aria-label*="Share"]').last
        
        # 2. Smart Polling mit doppelter Sicherung
        elapsed_minutes = 0
        while True:
            if page.is_closed(): return "Error: Browser closed."
            # Prüfen, ob Gemini noch schreibt (Stopp-Button sichtbar)
            is_busy = await page.locator('button[aria-label*="Stopp"], button[aria-label*="Stop"]').first.is_visible()
            is_share_visible = await share_btn.is_visible()
            
            # Er ist nur fertig, wenn er NICHT mehr schreibt UND der Share-Button da ist
            if not is_busy and is_share_visible:
                break 
                
            await asyncio.sleep(15)
            elapsed_minutes += 0.25
            if elapsed_minutes % 1 == 0:  # Jede volle Minute loggen
                print(f"[Browser] ... still researching ({int(elapsed_minutes)}m elapsed) ...")
        
        print(f"[Browser] ✅ Research finished after ~{elapsed_minutes} minutes!")

        # 6. Extraction
        if page.is_closed(): return "Error: Browser closed."
        print("[Browser] 📄 Extracting final report via UI Copy...")
        
        # Scroll to bottom again just to be sure
        await page.mouse.wheel(0, 5000)
        await asyncio.sleep(2)

        try:
            print("[Browser] 🖱️ Clicking 'Teilen und exportieren' menu...")
            await share_btn.scroll_into_view_if_needed()
            await share_btn.click()
            await asyncio.sleep(2) # Kurz warten, bis das Menü aufklappt
            
            copy_btn = page.locator('button:has-text("Inhalte kopieren"), span:has-text("Inhalte kopieren"), menuitem:has-text("kopieren")').last
            if await copy_btn.is_visible():
                print("[Browser] 🖱️ Clicking 'Inhalte kopieren' (Copy)...")
                await copy_btn.click()
                await asyncio.sleep(3) # Kurz warten, bis das Clipboard gefüllt ist
                
                # Clipboard auslesen
                clipboard_text = await page.evaluate("navigator.clipboard.readText()")
                if clipboard_text and len(clipboard_text) > 100:
                    print(f"[Browser] ✂️ Successfully extracted {len(clipboard_text)} characters from clipboard!")
                    return clipboard_text
            else:
                print("[Browser] ⚠️ 'Inhalte kopieren' nicht gefunden. Menü-Struktur hat sich geändert.")
                # Hier den bestehenden DOM-Fallback nutzen
        except Exception as e:
            print(f"[Browser] ⚠️ Clipboard extraction failed: {e}")

        # Fallback extraction (DOM)
        print("[Browser] ⚠️ Falling back to standard DOM extraction...")
        try:
            messages = page.locator('message-content')
            count = await messages.count()
            if count > 0:
                report_text = await messages.nth(count - 1).inner_text()
                if len(report_text) > 100:
                    print(f"[Browser] ✂️ Successfully extracted {len(report_text)} characters via DOM.")
                    return report_text
        except Exception as e:
            print(f"[Browser] ⚠️ DOM extraction error: {e}")

        print("[Browser] ⚠️ Using deep fallback text extraction...")
        return await page.evaluate("() => document.body.innerText")

class SimulatedBrowserProvider(BrowserSearchProvider):
    async def trigger_deep_research(self, prompt: str, tool: str = "gemini") -> str:
        print(f"[Browser] (Simulated) Mocking research for: {prompt}")
        return f"# Simulation Report\nFindings for '{prompt}'."
