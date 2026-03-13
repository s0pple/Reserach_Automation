import asyncio
import os
import logging
from playwright.async_api import async_playwright
from typing import Dict, Any
from pydantic import BaseModel, Field
from src.core.registry import ToolRegistry

logger = logging.getLogger(__name__)

class QwenResearchArgs(BaseModel):
    topic: str = Field(..., description="The research topic or question to investigate.")
    wait_minutes: int = Field(default=2, description="How long to wait for the deep research to complete.")

class QwenResearcher:
    """
    Spezialisierter Researcher für Qwen.ai unter Nutzung von Browser-Sessions
    zur Umgehung von Anti-Bot-Maßnahmen.
    """
    def __init__(self, profile_name: str = "google_searcher"):
        self.profile_dir = os.path.abspath(f"browser_sessions/{profile_name}")
        self.display = os.getenv("DISPLAY", ":99")

    async def perform_research(self, topic: str, wait_minutes: int = 2) -> Dict[str, Any]:
        logger.info(f"🚀 Starting Deep Research on: {topic}")
        
        async with async_playwright() as p:
            # Persistent Context lädt unsere Google-Sitzung
            # Wir stellen sicher, dass Playwright im Xvfb (:99) gerendert wird
            env = os.environ.copy()
            env["DISPLAY"] = self.display
            
            context = await p.chromium.launch_persistent_context(
                user_data_dir=self.profile_dir,
                headless=False,
                env=env,
                args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
            )
            page = context.pages[0] if context.pages else await context.new_page()
            await page.set_viewport_size({"width": 1280, "height": 1024})
            
            try:
                await page.goto('https://chat.qwen.ai/', wait_until='networkidle')
                await asyncio.sleep(5)
                
                # UI Cleanup (Banner-Kill)
                await page.add_style_tag(content="""
                    [class*="banner"], [class*="modal"], [class*="overlay"], [class*="Popup"] 
                    { display: none !important; visibility: hidden !important; }
                """)
                
                # Prompt eingeben
                prompt = f"FÜHRE EIN DEEP RESEARCH DURCH: {topic}. Erstelle einen extrem detaillierten, strukturierten Bericht."
                await page.locator("textarea, [contenteditable='true']").first.fill(prompt)
                await asyncio.sleep(1)
                await page.keyboard.press("Enter")
                
                # Senden-Button Fallback
                try:
                    send_btn = page.locator('button:has([class*="send"]), [class*="SendButton"]').first
                    if await send_btn.is_visible(): await send_btn.click()
                except: pass

                # Warten auf Generierung
                logger.info(f"⏳ Waiting {wait_minutes} minutes for generation...")
                await asyncio.sleep(wait_minutes * 60)
                
                # Extraktion
                report = await page.evaluate("""() => {
                    const bubbles = document.querySelectorAll('[class*="message-content"], [class*="content"]');
                    return Array.from(bubbles).map(b => b.innerText).join('\\n\\n--- SECTION ---\\n\\n');
                }""")
                
                return {
                    "success": True,
                    "topic": topic,
                    "content": report,
                    "length": len(report)
                }
                
            except Exception as e:
                logger.error(f"Research failed: {e}")
                return {"success": False, "error": str(e)}
            finally:
                await context.close()

# Wrapper für die Registry
async def qwen_research_tool(topic: str, wait_minutes: int = 2) -> Dict[str, Any]:
    researcher = QwenResearcher()
    return await researcher.perform_research(topic, wait_minutes)

# Automatische Registrierung beim Import ermöglichen
def register():
    ToolRegistry.register_tool(
        name="qwen_research",
        description="Führt eine tiefe Marktforschung oder detaillierte Analyse zu einem beliebigen Thema auf Qwen.ai durch. Nutze dieses Tool für komplexe Fragen und Berichte.",
        func=qwen_research_tool,
        schema=QwenResearchArgs
    )

if __name__ == "__main__":
    # Test-Run
    register()
    researcher = QwenResearcher()
    result = asyncio.run(researcher.perform_research("KI-Infrastruktur 2030"))
    print(f"Final Report Length: {result.get('length')} chars")
