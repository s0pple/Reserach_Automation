from typing import Any, List, Optional
from pydantic import Field
from ...core.tool_base import BaseTool, ToolArguments
from ...modules.browser.provider import BrowserSearchProvider

class BrowserSearchArguments(ToolArguments):
    """Arguments for the Browser Search tool."""
    query: str = Field(..., description="The search query or deep research prompt.")
    persona: str = Field("main", description="The browser persona/profile to use.")
    headless: bool = Field(True, description="Whether to run the browser in headless mode.")
    deep_research: bool = Field(False, description="Whether to trigger Gemini's Deep Research mode.")

class BrowserSearchTool(BaseTool):
    """
    A tool that uses a real browser (Playwright) to perform searches or deep research.
    """
    name: str = "browser_search"
    description: str = "Perform web searches or deep research using a real browser (Playwright)."
    args_schema: type[ToolArguments] = BrowserSearchArguments

    async def execute(self, args: BrowserSearchArguments) -> Any:
        provider = BrowserSearchProvider(headless=args.headless, persona=args.persona)
        
        if args.deep_research:
            return await provider.trigger_deep_research(args.query)
        else:
            return await provider.search_and_scrape(args.query)
