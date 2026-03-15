import json
import logging
from typing import Dict, Any
from ollama import AsyncClient

logger = logging.getLogger(__name__)

async def analyze_intent(user_command: str, model_name: str = "qwen3:8b") -> Dict[str, Any]:
    """
    Analyzes the user's intent and maps it to a registered tool using a local LLM via Ollama.
    Returns a dictionary with the tool name and extracted parameters.
    """
    # Import ToolRegistry inside to avoid circular dependencies if any
    from src.core.registry import ToolRegistry
    
    tools = ToolRegistry.get_all_tools()
    
    # Construct the tool descriptions for the prompt
    tool_descriptions = []
    for t in tools:
        tool_desc = (
            f"Tool Name: {t.name}\n"
            f"Description: {t.description}\n"
            f"Parameters Schema: {json.dumps(t.parameters, indent=2)}\n"
        )
        tool_descriptions.append(tool_desc)
        
    tools_prompt = "\n".join(tool_descriptions)

    system_prompt = f"""You are an intelligent routing assistant. 
Your task is to analyze the user command and select the most appropriate tool from the provided list.
You must extract any necessary parameters for the chosen tool based on its schema.

Available Tools:
{tools_prompt}

You must respond ONLY with a valid JSON object in the following format:
{{
  "tool": "name_of_the_tool",
  "parameters": {{
     "param1": "value1"
  }}
}}

If no tool matches the user's intent, return:
{{
  "tool": "error",
  "message": "No matching tool found"
}}
"""

    try:
        # Use a short timeout/client configuration if needed.
        # FIX: Use host.docker.internal to reach the host-based Ollama server
        client = AsyncClient(host="http://host.docker.internal:11434")
        response = await client.chat(
            model=model_name,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_command}
            ],
            format="json",
            options={
                "temperature": 0.0
            }
        )
        
        content = response['message']['content']
        parsed_intent = json.loads(content)
        return parsed_intent

    except Exception as e:
        logger.error(f"Router Error: {e}")
        # Robust Fallback - If router is offline, fallback to general_agent
        return {
            "tool": "general_agent",
            "parameters": {
                "goal": user_command
            }
        }
