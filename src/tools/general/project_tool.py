import os
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def get_project_status(query: str = None) -> Dict[str, Any]:
    """
    Reads the PROJECT_BOARD.md and returns the current status and open tasks.
    """
    try:
        paths = ["PROJECT_BOARD.md", "GEMINI.md", "README.md"]
        content = ""
        
        for path in paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    # Get first 2000 chars of each file for context
                    file_content = f.read(2000)
                    content += f"--- {path} ---\n{file_content}\n\n"
        
        if not content:
            return {"success": False, "error": "No project documentation found."}
            
        return {
            "success": True,
            "content": content,
            "summary": "Project status retrieved from local documentation."
        }
    except Exception as e:
        logger.error(f"Project Tool Error: {e}")
        return {"success": False, "error": str(e)}

def register():
    return {
        "name": "project_status_tool",
        "description": "Reads local project board, to-dos, and open tasks from PROJECT_BOARD.md and GEMINI.md.",
        "function": get_project_status
    }
