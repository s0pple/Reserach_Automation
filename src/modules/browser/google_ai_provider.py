import asyncio
import os
import time
import urllib.parse
from playwright.async_api import async_playwright, Page
from src.modules.browser.profile_manager import BrowserProfileManager

class GoogleAIProvider:
    """
    Automates standard Google Search specifically targeting the AI Overviews
    (AI Mode / udm=50 or similar parameters) to extract quick, high-quality
    summaries without hitting Gemini Deep Research limits.
    """
    def __init__(self, headless: bool = False, persona: str = "main"):
        self.headless = headless
        self.persona = persona
        self.profile_manager = BrowserProfileManager()
        self.user_data_dir = self.profile_manager.get_profile_path(persona)

    async def search_and_extract(self, query: str) -> str:
        """
        Performs a Google Search, waits for the AI Overview to generate, and extracts the text.
        """
        print(f"\n[GoogleAI] 🚀 Launching Chrome | Persona: '{self.persona.upper()}' | Headless: {self.headless}")

        async with async_playwright() as p:
            context = None
            try:
                context = await p.chromium.launch_persistent_context(
                    user_data_dir=self.user_data_dir,
                    headless=self.headless,
                    viewport={'width': 1280, 'height': 800},
                    args=[
                        "--disable-blink-features=AutomationControlled",
                        "--no-sandbox"
                    ]
                )

                page = context.pages[0] if context.pages else await context.new_page()
                page.set_default_timeout(30000)

                # Construct Google Search URL. 
                # Note: udm=50 / aep=48 are experimental flags often tied to AI features or specific UI layouts.
                # We also add standard query parameters.
                encoded_query = urllib.parse.quote(query)
                search_url = f"https://www.google.com/search?q={encoded_query}&hl=de"
                
                print(f"[GoogleAI] 🌐 Searching for: '{query}'")
                await page.goto(search_url, wait_until="load")

                # Handle Google Consent Cookie popup if it appears (mostly in EU)
                try:
                    consent_btn = page.locator('button:has-text("Alle ablehnen"), button:has-text("Alle akzeptieren")').first
                    if await consent_btn.is_visible(timeout=3000):
                        print("[GoogleAI] 🍪 Handling Cookie Consent...")
                        await consent_btn.click()
                        await asyncio.sleep(2)
                except: pass

                # Look for AI Overview trigger (sometimes you have to click "Generieren" / "Generate")
                try:
                    generate_btn = page.locator('button:has-text("Generieren"), button:has-text("Generate AI")').first
                    if await generate_btn.is_visible(timeout=3000):
                        print("[GoogleAI] ✨ Clicking AI 'Generate' button...")
                        await generate_btn.click()
                except: pass

                print("[GoogleAI] ⏳ Waiting for AI Overview to render...")
                # We wait for the specific AI block container. Google changes these classes often.
                # Common identifiers for AI Overviews:
                ai_selectors = [
                    'div[data-md="61"]', # Often used for AI blocks
                    'div:has-text("Generative KI ist experimentell")',
                    'div:has-text("Generative AI is experimental")',
                    '.g', # Fallback to top search result if AI fails
                ]
                
                # Give it time to type out the response
                await asyncio.sleep(8) 
                
                print("[GoogleAI] 📄 Extracting content...")
                
                # First try to find the expanding button "Show more" / "Mehr anzeigen"
                try:
                    more_btn = page.locator('button:has-text("Mehr anzeigen"), button:has-text("Show more")').first
                    if await more_btn.is_visible(timeout=2000):
                        await more_btn.click()
                        await asyncio.sleep(1)
                except: pass

                # Extract Text
                # We use a robust JS function to find the AI block by checking for specific text indicators
                extracted_text = await page.evaluate("""
                    () => {
                        // 1. Helper to find element by text
                        const findByText = (selector, text) => {
                            const elements = document.querySelectorAll(selector);
                            return Array.from(elements).find(el => el.innerText.includes(text));
                        };

                        // 2. Try to find the AI Overview container
                        // Common patterns: data-md="61" or specific experimental headers
                        let aiBlock = document.querySelector('div[data-md="61"]');
                        if (!aiBlock) {
                            aiBlock = findByText('div', 'Generative KI ist experimentell') || 
                                      findByText('div', 'Generative AI is experimental');
                        }

                        if (aiBlock) {
                            // Try to get the actual answer part (usually the first few paragraphs)
                            return aiBlock.innerText;
                        }
                        
                        // Attempt 3: Just grab the main search content area if AI block is not distinct
                        let mainBlock = document.querySelector('#search');
                        if (mainBlock) {
                            // Remove some noise like ads or sidebars if possible
                            return mainBlock.innerText.substring(0, 4000);
                        }
                        
                        return "Failed to extract search results content.";
                    }
                """)
                
                if extracted_text and len(extracted_text) > 50:
                    print(f"[GoogleAI] ✅ Extracted {len(extracted_text)} characters.")
                    return extracted_text
                else:
                    # Fallback to pure body text
                    print("[GoogleAI] ⚠️ AI block not found cleanly. Extracting general page text.")
                    return await page.evaluate("() => document.body.innerText.substring(0, 3000)")

            except Exception as e:
                print(f"[GoogleAI] ❌ Search Error: {e}")
                return f"Error during search: {e}"
            finally:
                if context:
                    await asyncio.sleep(1)
                    await context.close()
