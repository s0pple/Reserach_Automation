from ..core.tool_base import BaseTool, ToolArguments
from ..core.registry import ToolRegistry
from .web_scraper.browser_tool import BrowserSearchTool
from .cv_bot.cv_bot_tool import CVBotTool

# Wir lassen die automatische Registrierung der neuen Tools vorerst weg oder machen sie abhängig vom ToolRegistry Format.
# ToolRegistry.register_tool(...)

