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
        {"step": 1, "action": "shell_command", "command": "chromium --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1280,1200 --force-device-scale-factor=1 --incognito --app=\"https://www.google.com/search?q=Was+ist+vertikale+Landwirtschaft%3F\""},
        {"step": 2, "action": "wait", "duration": 5.0}, # Wait for results to load
        # Focus window
        {"step": 3, "action": "click", "x": 500, "y": 10}, 
        # Clear any prompts
        {"step": 4, "action": "type", "text": "esc"},
        # Scroll down more to ensure buttons are visible
        {"step": 5, "action": "type", "text": "pagedown"},
        {"step": 6, "action": "type", "text": "pagedown"},
        {"step": 7, "action": "wait", "duration": 1.0},
        # Try to accept cookies if banner is there (Self-healing will trigger if target is visible)
        {"step": 8, "target": "The blue button with the exact text 'Alle akzeptieren' in the bottom-right of the dialog", "action": "click"},
        {"step": 9, "action": "type", "text": "enter"},
        {"step": 10, "action": "wait", "duration": 1.0},
        {"step": 11, "action": "type", "text": "tab"},
        {"step": 12, "action": "type", "text": "enter"},
        {"step": 13, "action": "wait", "duration": 5.0},
        # Extract the results
        {"step": 14, "action": "extract_clipboard"}
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