import sys
import os
import asyncio
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.cv_bot.workflow_manager import WorkflowManager, WORKFLOW_DIR

async def main():
    print("🤖 Preparing Test Workflow...")
    load_dotenv()
    
    workflow_name = "open_calculator"
    workflow_steps = [
        {"step": 1, "target": "Windows Start Button", "action": "click"},
        {"step": 2, "action": "type", "text": "Rechner"},
        {"step": 3, "action": "type", "text": "enter"}
    ]
    
    # Save the workflow to JSON first
    filepath = os.path.join(WORKFLOW_DIR, f"{workflow_name}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(workflow_steps, f, indent=4)
        
    print(f"✅ Saved workflow '{workflow_name}' to {filepath}\n")
    
    # Initialize Manager and execute
    manager = WorkflowManager()
    await manager.execute_workflow(workflow_name)

if __name__ == "__main__":
    asyncio.run(main())