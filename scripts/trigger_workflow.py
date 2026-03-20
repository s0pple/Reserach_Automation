import asyncio
import os
import sys
# Add project root to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from scripts.crucible_loop import run_workflow, ALLOWED_IDS

async def manual_trigger():
    chat_id = ALLOWED_IDS[0] if ALLOWED_IDS else 12345
    goal = "Sag mir: Was ist 2+2?"
    print(f"Manually triggering workflow for goal: '{goal}' (Chat ID: {chat_id})")
    
    result = await run_workflow(goal, chat_id)
    print(f"Result: {result}")

if __name__ == "__main__":
    asyncio.run(manual_trigger())