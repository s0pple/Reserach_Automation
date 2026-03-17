import json
import logging
import os
import subprocess
import asyncio
from typing import Dict, Any, List, Optional, Callable
from src.core.secret import generate_content_with_key_rotation

logger = logging.getLogger(__name__)

class DeveloperAgent:
    """
    A reasoning agent that can explore the repository, read files, and answer 
    complex questions about the codebase or system.
    """
    
    def __init__(self):
        self.max_steps = 7
        self.context_window = 10 # Keep track of last N actions
        self.system_prompt = """You are the Lead Architect of the Phalanx 3.0 System (OpenClaw Architecture).
Your goal is to answer the user's question or fulfill their request by exploring the local repository.
You have a set of TOOLS to navigate the filesystem and understand the logic.

Available Tools:
- 'LIST_DIR': Lists contents of a directory. (Params: path)
- 'READ_FILE': Reads the content of a file. (Params: path, start_line, end_line)
- 'GREP': Searches for a string pattern in the repo. (Params: pattern, path)
- 'RUN_SHELL': Runs a short shell command. (Params: command)
- 'ANSWER': Final answer to the user. (Params: text)

### GUIDELINES
1.  **Reasoning First**: Start by explaining what you are looking for.
2.  **Surgical Reads**: Don't read huge files entirely if not needed.
3.  **Autonomy**: If you see a bug or missing logic, propose a fix or run a test.
4.  **Code Context**: You have access to the ENTIRE repo. If asked "how does X work?", find the code for X and explain it.

You MUST respond ONLY with a valid JSON object:
{
  "thought": "Your reasoning process",
  "tool": "LIST_DIR" | "READ_FILE" | "GREP" | "RUN_SHELL" | "ANSWER",
  "parameters": { ... }
}
"""

    async def run(self, user_goal: str, telegram_callback: Optional[Callable] = None) -> Dict[str, Any]:
        """
        Runs the ReAct loop (Reasoning -> Action -> Observation).
        """
        history = []
        step = 0
        
        if telegram_callback:
            await telegram_callback(f"🛠️ **Dev-Agent startet...**\n`{user_goal}`")
            
        while step < self.max_steps:
            step += 1
            
            # Prepare context for Gemini
            context = "\n".join([f"Step {h['step']}: Action={h['tool']} -> Result={h['result'][:500]}..." for h in history[-self.context_window:]])
            
            prompt = f"""{self.system_prompt}

### CURRENT GOAL
{user_goal}

### HISTORY (Last {self.context_window} steps)
{context}

What is your next step? (Step {step}/{self.max_steps})
"""
            try:
                # Use Gemini Flash for large context (Repo Analysis)
                response = generate_content_with_key_rotation(
                    prompt_parts=[prompt],
                    generation_config={"response_mime_type": "application/json"}
                )
                
                plan = json.loads(response.text.strip())
                thought = plan.get("thought", "Thinking...")
                tool = plan.get("tool", "ANSWER")
                params = plan.get("parameters", {})
                
                logger.info(f"[DevAgent] Step {step}: {thought} -> {tool}")
                
                if telegram_callback:
                    # Filter 'thought' to avoid too much spam, or just show key steps
                    if tool != "ANSWER":
                         await telegram_callback(f"🧠 **Gedanke:** {thought}\n🛠️ **Aktion:** `{tool}`")

                if tool == "ANSWER":
                    return {"success": True, "answer": params.get("text", "No answer provided.")}

                # Execute Action
                result = await self._execute_tool(tool, params)
                
                history.append({
                    "step": step,
                    "tool": tool,
                    "result": str(result)
                })
                
            except Exception as e:
                logger.error(f"[DevAgent] Loop error: {e}")
                return {"success": False, "error": str(e)}
                
        return {"success": False, "error": "Max reasoning steps reached without answer."}

    async def _execute_tool(self, tool: str, params: Dict[str, Any]) -> str:
        """Executes the low-level dev tools."""
        try:
            if tool == "LIST_DIR":
                path = params.get("path", ".")
                return str(os.listdir(path))
            
            elif tool == "READ_FILE":
                path = params.get("path")
                if not path: return "Error: No path provided."
                with open(path, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    start = params.get("start_line", 1) - 1
                    end = params.get("end_line", len(lines))
                    return "".join(lines[start:end])
            
            elif tool == "GREP":
                pattern = params.get("pattern")
                path = params.get("path", ".")
                # Safe grep call
                process = subprocess.run(["grep", "-rn", pattern, path], capture_output=True, text=True, timeout=10)
                return process.stdout if process.stdout else "No matches found."
            
            elif tool == "RUN_SHELL":
                command = params.get("command")
                # Simple shell runner for dev tasks (tests, etc)
                process = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
                return f"STDOUT: {process.stdout}\nSTDERR: {process.stderr}"
                
            return f"Error: Tool {tool} not implemented."
            
        except Exception as e:
            return f"Tool Error: {str(e)}"
