import sys
import os
import asyncio
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.cv_bot.workflow_manager import WorkflowManager, WORKFLOW_DIR

async def main():
    print("🌐 Preparing Web-Navigation Workflow...")
    load_dotenv()
    
    workflow_name = "google_search"
    workflow_steps = [
        {"step": 1, "action": "shell_command", "command": "chromium --no-sandbox --disable-dev-shm-usage \"https://www.google.com/\""},
        {"step": 2, "action": "wait", "duration": 5.0}, # Wait for Chrome and Google to load
        # The critical self-healing step: Find the search bar
        {"step": 3, "target": "The main Google Search Bar in the middle of the screen", "action": "click"},
        {"step": 4, "action": "type", "text": "Was ist vertikale Landwirtschaft?"},
        {"step": 5, "action": "type", "text": "enter"},
        {"step": 6, "action": "wait", "duration": 4.0}, # Wait for Google to load results
        {"step": 7, "action": "extract_clipboard"}
    ]
    
    # Save the workflow to JSON first
    filepath = os.path.join(WORKFLOW_DIR, f"{workflow_name}.json")
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(workflow_steps, f, indent=4)
        
    print(f"✅ Saved workflow '{workflow_name}' to {filepath}\n")
    
    # Initialize Manager and execute
    manager = WorkflowManager()
    result = await manager.execute_workflow(workflow_name)
    
    print("\n" + "="*50)
    print("📊 EXTRACTION RESULT")
    print("="*50)
    if result.get("success") and result.get("extracted_text"):
        text = result["extracted_text"]
        print(f"Total length: {len(text)} characters")
        print("First 500 chars:\n")
        print(text[:500] + "...")
    else:
        print("❌ No text extracted or workflow failed.")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())