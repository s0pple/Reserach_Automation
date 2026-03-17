from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel, Field
import logging
from src.agents.developer.agent import DeveloperAgent

logger = logging.getLogger(__name__)

class DeveloperArguments(BaseModel):
    query: str = Field(..., description="The technical question or request about the repository or system.")

async def developer_reasoning_tool(query: str, telegram_callback: Optional[Callable] = None) -> Dict[str, Any]:
    """
    Triggers the Developer Reasoning Agent to explore the repo and answer questions.
    """
    logger.info(f"[DeveloperTool] Starting reasoning for: {query}")
    
    agent = DeveloperAgent()
    result = await agent.run(query, telegram_callback=telegram_callback)
    
    if result.get("success"):
        return {"content": result.get("answer")}
    else:
        return {"error": result.get("error")}
