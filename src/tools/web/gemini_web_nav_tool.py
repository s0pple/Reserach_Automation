from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel, Field
import logging
import shlex
from src.tools.general.session_tool import tmux_manager

logger = logging.getLogger(__name__)

class WebNavArguments(BaseModel):
    goal: str = Field(..., description="The goal for the autonomous web browsing agent (e.g. 'Get Bitcoin Price').")

async def gemini_web_nav_tool(goal: str = None, query: str = None, telegram_callback: Optional[Callable] = None, **kwargs) -> Dict[str, Any]:
    """
    Starts the autonomous Gemini Web Navigation Loop in a tmux session.
    """
    # Robust parameter handling
    target_goal = goal or query or kwargs.get("instruction")
    if not target_goal:
        return {"error": "Missing 'goal' or 'query' parameter."}
        
    logger.info(f"[WebNav] Starting loop for: {target_goal}")
    
    session_id = "web_nav_agent"
    
    # Check if already running? Maybe kill it first to be clean
    existing = tmux_manager.get_session(session_id)
    if existing:
        await tmux_manager.execute({"action": "kill", "session_id": session_id})
        
    safe_goal = shlex.quote(target_goal)
    result = await tmux_manager.execute({
        "action": "start",
        "session_id": session_id,
        "command": f"python3 scripts/web_nav_loop.py {safe_goal}"
    }, telegram_callback)
    
    if result.get("success"):
        return {"content": f"🚀 **Gemini Web Nav Agent gestartet!**\nZiel: `{target_goal}`\nScreenshots folgen..."}
    else:
        return {"error": result.get("error")}
