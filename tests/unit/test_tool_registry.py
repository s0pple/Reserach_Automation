import asyncio
from src.core.registry import ToolRegistry
from src.tools.dummy_tools import register_dummy_tools, CVClickArgs, VentureAnalysisArgs

async def test_registry():
    print("🧪 Testing New Tool Registry...")
    
    # 1. Register dummy tools
    register_dummy_tools()
    
    # 2. List tools
    tools = ToolRegistry.list_tools()
    print(f"  Available Tools: {tools}")
    
    # 3. Get a tool and its metadata
    cv_info = ToolRegistry.get_tool("cv_click")
    if cv_info:
        print(f"  Tool Name: {cv_info.name}")
        print(f"  Description: {cv_info.description}")
        print(f"  Parameters Schema: {cv_info.parameters}")
        
        # 4. Simulate execution
        print("  Executing CV Click (Simulated)...")
        args = {"target": "Warenkorb"}
        result = await cv_info.func(args)
        print(f"  Result: {result}")

    venture_info = ToolRegistry.get_tool("venture_analysis")
    if venture_info:
        print(f"  Tool Name: {venture_info.name}")
        print("  Executing Venture Analysis (Simulated)...")
        args = {"domain": "AI Logistics"}
        result = await venture_info.func(args)
        print(f"  Result: {result}")

if __name__ == "__main__":
    asyncio.run(test_registry())
