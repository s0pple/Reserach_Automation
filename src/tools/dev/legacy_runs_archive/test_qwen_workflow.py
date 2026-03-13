import sys
import os
import asyncio
import json
from dotenv import load_dotenv

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.tools.cv_bot.workflow_manager import WorkflowManager, WORKFLOW_DIR

async def main():
    print("🌐 Preparing Qwen Web-Navigation Workflow...")
    load_dotenv()
    
    workflow_name = "qwen_deep_research"
    workflow_steps = [
        # Step 1: Open Qwen
        {"step": 1, "action": "shell_command", "command": "chromium --no-sandbox --disable-dev-shm-usage --disable-gpu --window-size=1280,1200 --force-device-scale-factor=1 --incognito --app=\"https://chat.qwen.ai/\""},
        {"step": 2, "action": "wait", "duration": 8.0}, 
        
        # Step 3: Focus window
        {"step": 3, "action": "click", "x": 500, "y": 10}, 
        
        # Step 4: Clear any potential welcome popups or cookie banners
        {"step": 4, "action": "type", "text": "esc"},
        {"step": 5, "action": "wait", "duration": 1.0},
        
        # Step 6: Click exactly on the placeholder text coordinate
        {"step": 6, "action": "click", "x": 305, "y": 532},
        {"step": 7, "action": "wait", "duration": 1.0},
        
        # Step 8: Type prompt
        {"step": 8, "action": "type", "text": "how to enable deep research"},
        {"step": 9, "action": "wait", "duration": 1.0},
        
        # Step 10: Press Enter
        {"step": 10, "action": "type", "text": "enter"},
        
        # Step 11: Wait for response
        {"step": 11, "action": "wait", "duration": 15.0}, 
        
        # Step 12: Extract the results
        {"step": 12, "action": "extract_clipboard"}
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
        print("First 1000 chars:\n")
        print(text[:1000] + "...")
        
        # Save to file
        with open("qwen_output.txt", "w", encoding="utf-8") as f:
            f.write(text)
        print("✅ Saved full output to qwen_output.txt")
    else:
        print("❌ No text extracted or workflow failed.")
    print("="*50)

if __name__ == "__main__":
    asyncio.run(main())
