import os
import uvicorn
from fastapi import FastAPI
from mcp.server.fastmcp import FastMCP
from src.mcp.providers.gemini_browser import GeminiBrowser
from src.mcp.manager.status import StatusManager

# 1. Config & Setup
ACCOUNT_ID = os.getenv("ACCOUNT_ID", "default")
PORT = int(os.getenv("PORT", 8000))

# 2. Components
status_manager = StatusManager()
browser = GeminiBrowser(account_id=ACCOUNT_ID, status_manager=status_manager)

# 3. MCP Server Definition
mcp = FastMCP(f"Gemini-Browser-{ACCOUNT_ID}")

@mcp.tool()
async def ask_gemini(prompt: str) -> str:
    """
    Sends a prompt to Google AI Studio via the automated browser.
    Returns the generated text response.
    """
    # Check status first
    status = status_manager.get_status(ACCOUNT_ID)
    if status != "active":
        return f"ERROR: Account {ACCOUNT_ID} is currently '{status}'. Please wait or switch accounts."

    try:
        # Lazy start: Browser starts on first request if not running
        if not browser.page:
            await browser.start(headless=True)
            
        response = await browser.generate(prompt)
        return response

    except Exception as e:
        error_msg = str(e)
        print(f"[MCP-Server] Error processing request: {error_msg}")
        
        # Simple heuristic for rate limits or critical failures
        if "limit" in error_msg.lower() or "quota" in error_msg.lower():
            status_manager.set_status(ACCOUNT_ID, "limited", cooldown_hours=1)
            return "ERROR: Rate limit detected. Account set to cooldown."
            
        return f"ERROR: Browser automation failed: {error_msg}"

# 4. FastAPI Integration (for Healthchecks & SSE)
app = FastAPI()

@app.get("/health")
async def health_check():
    """Simple health check for Docker/Orchestrator."""
    is_browser_up = browser.page is not None
    status = status_manager.get_status(ACCOUNT_ID)
    return {
        "account": ACCOUNT_ID,
        "status": status,
        "browser_active": is_browser_up
    }

# Mount MCP as SSE (Standard way for FastMCP)
# This allows clients to connect via SSE to /sse
app.mount("/", mcp.app)

if __name__ == "__main__":
    print(f"🚀 Starting MCP Server for {ACCOUNT_ID} on port {PORT}...")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
