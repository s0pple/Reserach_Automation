from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel, Field
import asyncio
import logging

from src.tools.general.session_tool import tmux_manager

logger = logging.getLogger(__name__)

class AIStudioParams(BaseModel):
    instruction: str = Field(..., description="The natural language instruction for AI Studio (e.g., 'Switch model to Gemini 1.5', 'Create new chat').")
    session_id: Optional[str] = Field(None, description="Optional ID of the active tmux session. If not provided, will look for 'live_aistudio'.")

async def ai_studio_controller(instruction: str, session_id: str = "live_aistudio", telegram_callback: Callable = None) -> Dict[str, Any]:
    """
    Intelligent Agentic Wrapper for AI Studio.
    Translates natural language intent into low-level commands for the running 'live_aistudio.py' script.
    """
    
    # 1. Check if session exists
    session = tmux_manager.get_session(session_id)
    
    if not session:
        # Auto-Start logic if session doesn't exist
        logger.info(f"Session {session_id} not found. Starting it...")
        if telegram_callback:
            await telegram_callback("🔄 Starte AI Studio Controller (Headless Browser)...")
            
        start_result = await tmux_manager.execute({
            "action": "start",
            "session_id": session_id,
            "command": "python3 scripts/live_aistudio.py"
        }, telegram_callback)
        
        if not start_result.get("success"):
            return {"error": f"Failed to start AI Studio: {start_result.get('error')}"}
            
        # Wait for startup
        await asyncio.sleep(5)
        
    # 2. Translate Intent (Basic Heuristic for now, can be LLM-upgraded later)
    # We map user language -> script commands
    cmd_lower = instruction.lower()
    script_command = ""
    
    if any(k in cmd_lower for k in ["start", "open", "gehe", "öffne", "launch"]):
         # User just wants to ensure it's open. The auto-start block above handled it.
         # We can optionally send a refresh or just return success.
         # But the tool contract says we execute commands. 
         # The live_aistudio script waits for commands. 
         # Sending nothing is fine, just return success.
         return {"content": f"✅ AI Studio ist bereit und geöffnet."}

    elif "neu" in cmd_lower or "new" in cmd_lower or "chat" in cmd_lower:
        script_command = "new"
    elif "model" in cmd_lower or "modell" in cmd_lower or "wechsel" in cmd_lower:
        # Extract model name
        model_name = "gemini 1.5 pro" # Default fallback
        try:
            if "zu" in cmd_lower:
                parts = cmd_lower.split("zu")
                if len(parts) > 1: model_name = parts[1].strip()
            elif "model" in cmd_lower:
                 parts = cmd_lower.split("model")
                 if len(parts) > 1: model_name = parts[1].strip()
            elif "modell" in cmd_lower:
                 parts = cmd_lower.split("modell")
                 if len(parts) > 1: model_name = parts[1].strip()
            
            # Clean up punctuation (e.g. "gemini 3.1 pro.")
            model_name = model_name.rstrip(".,?!")
            
        except Exception:
            logger.warning(f"Could not parse model name from '{instruction}', using fallback.")
            
        script_command = f"model {model_name}"
             
    elif "schreib" in cmd_lower or "type" in cmd_lower or "prompt" in cmd_lower:
        # "Schreibe Hallo Welt"
        if "schreib" in cmd_lower:
             text = instruction.split("schreib", 1)[1].strip()
        elif "type" in cmd_lower:
             text = instruction.split("type", 1)[1].strip()
        else:
             text = instruction
        script_command = f"type {text}"
        
    elif "send" in cmd_lower or "absenden" in cmd_lower:
        script_command = "send"
        
    elif "exit" in cmd_lower or "stop" in cmd_lower:
        script_command = "exit"
        
    else:
        # If no keyword matches, assume it's a prompt to be typed?
        # Or ask for clarification. For now, assume it's a prompt if long.
        if len(instruction) > 10:
             script_command = f"type {instruction}"
        else:
             return {"error": f"Konnte Befehl nicht verstehen: '{instruction}'. Nutze: 'Neuer Chat', 'Modell [Name]', 'Schreibe [Text]'."}

    # 3. Execute Command via Tmux Input
    # We simplify: If it's a known keyword, use it. Else, treat as 'prompt'.
    
    final_cmd = ""
    if any(k in cmd_lower for k in ["new", "neu", "chat", "reset"]):
        final_cmd = "new"
    elif any(k in cmd_lower for k in ["exit", "stop", "quit"]):
        final_cmd = "exit"
    elif any(k in cmd_lower for k in ["screenshot", "bild", "zeig"]):
        final_cmd = "screenshot"
    elif any(k in cmd_lower for k in ["finde", "wo ist", "analysiere", "schau dir an", "reflection", "reflect"]):
        # This triggers the Visual Reflection loop (Screenshot -> Upload -> Question)
        final_cmd = f"reflect {instruction}"
    else:
        # Treat everything else as a prompt
        if cmd_lower.startswith("prompt ") or cmd_lower.startswith("type "):
            final_cmd = instruction
        else:
            final_cmd = f"prompt {instruction}"
            
    logger.info(f"Sending command to AI Studio: {final_cmd}")
    
    # Send the command
    await tmux_manager.execute({
        "action": "input",
        "session_id": session_id,
        "input_text": final_cmd + "\n"
    })
    
    return {
        "content": f"✅ Anweisung gesendet: `{final_cmd}`\n(Warte auf visuelle Antwort im Chat...)"
    }
