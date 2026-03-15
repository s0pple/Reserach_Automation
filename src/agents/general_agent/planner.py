import json
import logging
from typing import Dict, Any, List
from src.core.secret import generate_content_with_key_rotation

logger = logging.getLogger(__name__)

class PlanningAgent:
    """
    The Brain of the General Agent.
    Uses Gemini API in strict JSON mode to plan the next best action based on the current state.
    """
    
    def __init__(self):
        self.system_prompt = """You are an autonomous web-agent architect. Your task is to navigate the web to achieve the user's goal.
You are given the user's goal, the current URL, and the result of the previous action.
Based on this information, you must decide the NEXT SINGLE LOGICAL STEP.

You have two main tool types at your disposal:
1. 'DOM_SCRAPE': Fast and cheap. Use this to extract text, lists, or simple data from standard websites (like Wikipedia, directories).
2. 'VISION_CLICK': Uses computer vision and OS-level clicks. Use this for complex web apps (like Migros, Qwen), bot-protected sites, clicking buttons, typing into search bars, or bypassing cookie banners.

Your response MUST be a valid JSON object matching this schema:
{
  "thought_process": "A brief reasoning of why this is the next best step",
  "next_action": "GOTO_URL" | "SEARCH" | "CLICK" | "EXTRACT" | "FINISH",
  "tool_preference": "DOM_SCRAPE" | "VISION_CLICK",
  "target": "The URL, the search term, or the visual description of the element to interact with",
  "expected_result": "What should the state look like after this action succeeds?"
}
"""

    def plan_next_step(self, goal: str, current_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calls Gemini to get the next step in JSON format.
        """
        logger.info(f"[Planner] Planning next step for goal: '{goal}'")
        
        prompt = f"""{self.system_prompt}

### CURRENT CONTEXT
User Goal: {goal}
Current URL: {current_state.get('url', 'None (Browser not started yet)')}
Last Action Result: {current_state.get('last_action_result', 'None')}

What is the next action?
"""
        try:
            response = generate_content_with_key_rotation(
                prompt_parts=[prompt],
                generation_config={"response_mime_type": "application/json"}
            )
            
            plan_json_str = response.text.strip()
            plan = json.loads(plan_json_str)
            logger.info(f"[Planner] Decided next step: {plan.get('next_action')} via {plan.get('tool_preference')} -> Target: {plan.get('target')}")
            return plan
            
        except Exception as e:
            logger.error(f"[Planner] Failed to generate plan: {e}")
            return {
                "thought_process": "Error generating plan",
                "next_action": "ERROR",
                "tool_preference": "NONE",
                "target": str(e),
                "expected_result": "Recovery needed"
            }
