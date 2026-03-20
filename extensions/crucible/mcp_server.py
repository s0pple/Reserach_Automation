from mcp.server.fastmcp import FastMCP
from playwright.async_api import async_playwright, Page, expect
import asyncio

# Create the MCP Server
mcp = FastMCP("The Crucible")

# Reuse our proven logic from test_ai_studio_streaming.py
INPUT_SELECTOR = "textarea[aria-label='Enter a prompt']"
RUN_BUTTON_SELECTOR = "button[aria-label='Run']"

async def _ask_google_ai(page: Page, prompt: str) -> str:
    """Internal helper to drive the browser."""
    # ... (Logic from test_ai_studio_streaming.py goes here) ...
    await page.fill(INPUT_SELECTOR, prompt)
    await page.keyboard.press("Control+Enter")
    
    # Wait for Start (Button disappears)
    run_btn = page.locator(RUN_BUTTON_SELECTOR)
    await expect(run_btn).to_be_hidden()
    
    # Wait for End (Button reappears)
    await run_btn.wait_for(state="visible", timeout=120000)
    
    # Extract
    text = await page.locator("ms-text-chunk").last.inner_text()
    return text

@mcp.tool()
async def ask_cloud_llm(prompt: str) -> str:
    """
    Sends a prompt to the free Google AI Studio cloud LLM and returns the response.
    Uses a headless browser to automate the interaction.
    """
    async with async_playwright() as p:
        # Launch persistent context to keep login session
        browser = await p.chromium.launch_persistent_context(
            user_data_dir="/app/browser_sessions/account_cassie",
            headless=True # Headless in production
        )
        page = browser.pages[0]
        await page.goto("https://aistudio.google.com/app/prompts/new_chat")
        
        response = await _ask_google_ai(page, prompt)
        
        await browser.close()
        return response

if __name__ == "__main__":
    # Runs the server on Stdio (standard input/output) for OpenClaw to connect
    mcp.run()
