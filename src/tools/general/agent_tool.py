from src.core.registry import ToolRegistry
from src.agents.general_agent.executor import GeneralExecutor
import logging
import json
from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)

class GeneralAgentArguments(BaseModel):
    goal: str = Field(..., description="The exact goal the user wants to achieve (e.g. 'Finde den Preis von Bananen bei Migros').")

async def general_agent_tool(goal: str, telegram_callback=None, **kwargs):
    """
    Execution for the General Agent (Phase 1, 2 & 3).
    Runs the Planner -> Executor loop.
    """
    logger.info(f"[GeneralAgent] Received goal: {goal}")
    
    executor = GeneralExecutor()
    initial_state = {
        "url": "None",
        "last_action_result": "Initial start"
    }
    
    if telegram_callback:
        await telegram_callback(f"🧠 **General Agent startet...**\n**Ziel:** `{goal}`")
        
    result = await executor.run(goal, initial_state, telegram_callback=telegram_callback)
    
    if result.get("success"):
        content = f"✅ **Mission erfolgreich!**\n**Ergebnis:** {result.get('result')}"
    else:
        content = f"❌ **Mission fehlgeschlagen.**\n**Grund:** {result.get('error')}"
    
    return {
        "success": result.get("success"),
        "content": content,
        "length": len(content)
    }

def register():
    """Registers the General Agent with the global Tool Registry."""
    ToolRegistry.register_tool(
        name="general_agent",
        description="A universal agent that can surf the web, use DOM scraping or Vision to accomplish arbitrary tasks, research products, or buy things.",
        func=general_agent_tool,
        schema=GeneralAgentArguments
    )
