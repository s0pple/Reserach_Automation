from typing import Any, Dict, Optional, Callable
from pydantic import BaseModel, Field
import asyncio
import logging

from src.tools.general.session_tool import tmux_manager

logger = logging.getLogger(__name__)

class AIStudioParams(BaseModel):
    instruction: str = Field(..., description="The natural language instruction for AI Studio.")

async def ai_studio_controller(instruction: str, session_id: str = "aistudio_bridge", telegram_callback: Callable = None) -> Dict[str, Any]:
    """
    Force EVERY instruction into the 'auto' reasoning loop for robustness.
    """
    cmd_lower = instruction.lower()
    
    # 1. Utility Commands (No Loop)
    if any(k in cmd_lower for k in ["stop", "beende", "abbruch", "halt", "stopp"]):
        final_cmd = "stop"
    elif any(k in cmd_lower for k in ["new", "neu", "reset"]):
        final_cmd = "new"
    elif any(k in cmd_lower for k in ["screenshot", "bild", "zeig"]):
        final_cmd = "screenshot"
    else:
        # 2. DEFAULT: Force Auto Loop
        # If user says "Wechsle Modell", we send "auto Wechsle Modell"
        if instruction.startswith("auto "):
            final_cmd = instruction
        else:
            final_cmd = f"auto {instruction}"

    # Ensure session exists
    session = tmux_manager.get_session(session_id)
    if not session:
        if telegram_callback:
            await telegram_callback(f"🔄 Starte Grounded Explorer Session...")
        await tmux_manager.execute({
            "action": "start",
            "session_id": session_id,
            "command": "cd /app && export PYTHONPATH=/app && python3 scripts/live_aistudio.py"
        })
        await asyncio.sleep(8)

    # Execute
    logger.info(f"[AIStudioTool] Sending to tmux: {final_cmd}")
    await tmux_manager.execute({
        "action": "input",
        "session_id": session_id,
        "input_text": final_cmd + "\n"
    })
    
    return {
        "content": f"⚙️ **Anweisung verarbeitet:** `{final_cmd}`"
    }
