import subprocess
import logging
import os
import asyncio
from typing import Dict, Any

logger = logging.getLogger(__name__)

async def run_cli_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """
    Executes a shell command and returns the output.
    """
    logger.info(f"🛠️ Executing CLI Command: {command}")
    
    try:
        # Run command asynchronously to avoid blocking the bot
        process = await asyncio.create_subprocess_shell(
            command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            executable='/bin/bash'
        )
        
        try:
            stdout, stderr = await asyncio.wait_for(process.communicate(), timeout=timeout)
            
            result = {
                "success": process.returncode == 0,
                "stdout": stdout.decode().strip() if stdout else "",
                "stderr": stderr.decode().strip() if stderr else "",
                "exit_code": process.returncode
            }
            
            # Limit output size for Telegram
            if len(result["stdout"]) > 3000:
                result["stdout"] = result["stdout"][:1500] + "\n... [TRUNCATED] ...\n" + result["stdout"][-1500:]
            
            return result
            
        except asyncio.TimeoutError:
            process.kill()
            return {"success": False, "error": f"Command timed out after {timeout}s"}
            
    except Exception as e:
        logger.error(f"💥 CLI Tool Error: {e}")
        return {"success": False, "error": str(e)}

def register():
    """Registration for the tool registry if needed."""
    return {
        "name": "cli_tool",
        "description": "Executes shell commands directly on the server.",
        "function": run_cli_command
    }
