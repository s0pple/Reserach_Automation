import asyncio
import sys
import os
import json
import logging
from datetime import datetime
import aioconsole

# Ensure the root directory is in sys.path so 'src' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.core.registry import ToolRegistry
from src.agents.local_router.router import analyze_intent
from pydantic import BaseModel, Field
from typing import Dict, Any, Optional

# --- REAL TOOLS IMPORT ---
from runs.run_venture_analyst import run_big_bang

# Setup Logging
logger = logging.getLogger("Orchestrator")

# --- CV BOT IMPLEMENTATION ---
def sync_cv_action(action: str, target: Optional[str] = None, x: Optional[int] = None, y: Optional[int] = None):
    """
    Synchronous, blocking function for Computer Vision and GUI interaction.
    Uses pyautogui and cv2 safely within its own thread.
    """
    print(f"🤖 [CV-Bot Thread] Initializing...")
    try:
        import pyautogui
        import cv2
        print("🤖 [CV-Bot Thread] cv2 & pyautogui geladen.")
    except ImportError:
        print("🤖 [CV-Bot Thread] ⚠️ cv2 oder pyautogui fehlt. Simuliere Aktion.")

    print(f"🤖 [CV-Bot Thread] Führe Aktion aus: {action} auf {target or (x, y)}...")
    import time
    time.sleep(2) # Simulating heavy blocking CV work
    print(f"🤖 [CV-Bot Thread] Aktion '{action}' abgeschlossen!")
    
    return {"status": "success", "action": action, "target": target}

async def async_cv_wrapper(args: Dict[str, Any]):
    """
    Asynchronous wrapper that offloads the blocking CV code to a separate thread
    so it doesn't freeze the main asyncio event loop.
    """
    action = args.get("action", "click")
    target = args.get("target")
    x = args.get("x")
    y = args.get("y")
    
    print(f"⏳ Delegating CV task '{action}' to background thread...")
    # AWAIT asyncio.to_thread to keep the main event loop running!
    result = await asyncio.to_thread(sync_cv_action, action, target, x, y)
    return result

# --- Pydantic Schemas for Real Tools ---
class VentureAnalysisArgs(BaseModel):
    domain: str = Field(..., description="The industry or market domain to analyze.")

class CVBotArgs(BaseModel):
    action: str = Field(..., description="Action to perform: 'screenshot', 'click', 'type', 'find_element'.")
    target: Optional[str] = Field(None, description="Name of the UI element or image to find.")
    x: Optional[int] = Field(None, description="X coordinate.")
    y: Optional[int] = Field(None, description="Y coordinate.")

class DeepResearchArgs(BaseModel):
    prompt: str = Field(..., description="The comprehensive topic or prompt for Gemini to deeply research.")
    headless: bool = Field(False, description="Whether to run the browser invisibly. Default is False so the user can see the progress.")

# --- TOOL REGISTRATION ---
def setup_tools():
    # 1. Venture Analyst
    async def run_venture_wrapper(args: Dict[str, Any]):
        domain = args.get("domain")
        print(f"🧠 [Venture] Starte Analyse für: {domain}")
        await run_big_bang(domain)
        return {"status": "success", "domain": domain}

    ToolRegistry.register_tool(
        name="venture_analysis",
        description="Performs deep market analysis and venture capital memo generation for a specific domain.",
        func=run_venture_wrapper,
        schema=VentureAnalysisArgs
    )

    # 2. CV Bot
    ToolRegistry.register_tool(
        name="cv_bot",
        description="Interact with the local computer screen using computer vision (OpenCV) and automation (clicks, typing).",
        func=async_cv_wrapper,
        schema=CVBotArgs
    )

    # 3. Gemini Deep Research
    async def run_deep_research_wrapper(args: Dict[str, Any]):
        from src.modules.browser.provider import BrowserSearchProvider
        prompt = args.get("prompt")
        headless = args.get("headless", False)
        
        print(f"🔍 [Deep Research] Starte Browser Automation für: '{prompt}'")
        dr_browser = BrowserSearchProvider(headless=headless, persona="main")
        
        try:
            final_report = await dr_browser.trigger_deep_research(prompt=prompt, tool="gemini")
            
            # Save Final Report
            safe_topic = prompt[:30].replace(" ", "_").replace("/", "").lower()
            dr_filepath = f"reports/standalone_deep_research_{safe_topic}.md"
            os.makedirs(os.path.dirname(dr_filepath), exist_ok=True)
            
            with open(dr_filepath, "w", encoding="utf-8") as f:
                f.write(final_report)
            print(f"\n✅ [DEEP RESEARCH SAVED] {dr_filepath}")
            return {"status": "success", "file": dr_filepath}
        except Exception as e:
            print(f"❌ [Deep Research Failed] {e}")
            return {"status": "error", "message": str(e)}

    ToolRegistry.register_tool(
        name="gemini_deep_research",
        description="Opens a real Chrome browser, logs into Gemini, and triggers the powerful 'Deep Research' mode for comprehensive, long-form reports.",
        func=run_deep_research_wrapper,
        schema=DeepResearchArgs
    )

# --- SESSION LOGGING ---
def log_session_event(user_input: str, intent: dict, status: str):
    log_file = os.path.join(os.path.dirname(__file__), "logs", "session_log.jsonl")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    event = {
        "timestamp": datetime.now().isoformat(),
        "user_input": user_input,
        "tool_decision": intent.get("tool"),
        "parameters": intent.get("parameters", {}),
        "status": status
    }
    
    with open(log_file, "a", encoding="utf-8") as f:
        f.write(json.dumps(event) + "\n")

# --- MAIN ORCHESTRATOR LOOP ---
async def main():
    print("\n" + "="*50)
    print("🚀 RESEARCH AUTOMATION ORCHESTRATOR STARTED")
    print("="*50)
    
    setup_tools()
    print("\n[SYSTEM] Orchestrator is online. Type 'exit' or 'quit' to stop.")

    while True:
        try:
            # NON-BLOCKING input via aioconsole
            user_command = await aioconsole.ainput("\n> ")
            
            if not user_command.strip():
                continue
                
            if user_command.lower() in ['exit', 'quit']:
                print("🛑 Exiting Orchestrator. Goodbye!")
                break
                
            print("⏳ Analysiere Befehl via Local Router (Ollama)...")
            intent = await analyze_intent(user_command)
            
            tool_name = intent.get("tool")
            
            if tool_name == "error":
                print(f"❌ Router Fehler: {intent.get('message')}")
                log_session_event(user_command, intent, "failed")
                continue
                
            tool_info = ToolRegistry.get_tool(tool_name)
            
            if not tool_info:
                print(f"⚠️ Tool '{tool_name}' nicht in Registry gefunden!")
                log_session_event(user_command, intent, "tool_not_found")
                continue
                
            print(f"⚙️ Führe Tool '{tool_name}' aus mit Parametern: {intent.get('parameters', {})}")
            
            # Execute the tool
            try:
                result = await tool_info.func(intent.get("parameters", {}))
                print(f"✅ Tool '{tool_name}' erfolgreich abgeschlossen.")
                log_session_event(user_command, intent, "success")
            except Exception as e:
                print(f"❌ Fehler bei der Ausführung von '{tool_name}': {e}")
                log_session_event(user_command, intent, "execution_error")
                
        except asyncio.CancelledError:
            break
        except Exception as e:
            print(f"⚠️ Unerwarteter Fehler im Loop: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n🛑 Process interrupted by user.")
