import asyncio
import logging
from src.tools.web.gemini_web_nav_tool import gemini_web_nav_tool

logging.basicConfig(level=logging.INFO)

async def test():
    print("Testing gemini_web_nav_tool...")
    try:
        result = await gemini_web_nav_tool(goal="Test Bitcoin Price")
        print(f"Result: {result}")
    except Exception as e:
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test())
