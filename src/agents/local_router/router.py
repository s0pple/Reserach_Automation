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

    # Note: We use double curly braces {{ }} to escape them in the f-string for JSON examples.
    system_prompt = f"""You are an intelligent routing assistant. 
Your task is to analyze the user command and select the most appropriate tool from the provided list.
You must extract any necessary parameters for the chosen tool based on its schema.

Available Tools:
{tools_prompt}

IMPORTANT MAPPING RULES:
- "status", "was läuft", "zeig jobs", "hallo", "hilfe", "funktionen", "welche tools", "was kannst du" -> Tool: project_status_tool
- "terminal", "console", "cli", "sessions" -> Tool: interactive_session_tool (action='list')
- "ai studio", "gemini", "modell wechseln", "neuer chat", "schreibe prompt", "stop", "beende", "aistudio" -> Tool: ai_studio_tool
- "research", "recherchiere", "google", "such nach", "deep research" -> Tool: deep_research
- "bitcoin preis", "kaufe tickets", "geh auf seite X", "navigiere", "browser task" -> Tool: web_nav_tool (Parameter: goal)
- "screenshot", "bildschirm", "watch", "zeig mir" -> Tool: watch_tool
- "how does X work", "explain the code", "find where Y is", "run a test", "fix this bug" -> Tool: developer_tool
- "open google", "gehe auf", "browse", "navigate to", "öffne <url>", "click on", "klicke", "type", "schreibe" -> Tool: general_agent

You must respond ONLY with a valid JSON object in the following format:
{{
  "thought": "Brief explanation of your reasoning process",
  "tool": "name_of_the_tool",
  "parameters": {{
     "goal": "The instruction or question"
  }}
}}

If no tool matches the user's intent, return:
{{
  "thought": "Reasoning why no tool matches",
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
            "thought": "Router failed or is offline. Falling back to General Agent.",
            "tool": "general_agent",
            "parameters": {
                "goal": user_command
            }
        }
