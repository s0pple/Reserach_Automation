from pydantic import BaseModel, Field
from typing import Any, Dict, Optional
from ..core.registry import ToolRegistry

# Schema for CV Click Tool
class CVClickArgs(BaseModel):
    target: str = Field(..., description="Name of the UI element to click (e.g., 'Warenkorb').")
    x: Optional[int] = Field(None, description="Optional X coordinate.")
    y: Optional[int] = Field(None, description="Optional Y coordinate.")

# Schema for Venture Analysis Tool
class VentureAnalysisArgs(BaseModel):
    domain: str = Field(..., description="The industry or market domain to analyze.")

# Implementations
async def cv_click(args: Dict[str, Any]):
    print(f"🤖 [Dummy] Clicking on '{args.get('target')}'...")
    return {"status": "success", "action": "click", "target": args.get('target')}

async def run_venture_analysis(args: Dict[str, Any]):
    print(f"🧠 [Dummy] Analyzing venture market: '{args.get('domain')}'...")
    return {"status": "success", "report": f"Market analysis for {args.get('domain')} completed."}

# Registration function
def register_dummy_tools():
    ToolRegistry.register_tool(
        name="cv_click",
        description="Clicks on a UI element on the screen using Computer Vision.",
        func=cv_click,
        schema=CVClickArgs
    )
    
    ToolRegistry.register_tool(
        name="venture_analysis",
        description="Performs a deep market analysis on a specific domain.",
        func=run_venture_analysis,
        schema=VentureAnalysisArgs
    )
