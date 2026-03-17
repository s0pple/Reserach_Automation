import json
import logging
from typing import Dict, Any, List
from src.core.secret import generate_content_with_key_rotation

logger = logging.getLogger(__name__)

class PlanningAgent:
    """
    The Brain of the General Agent (Multimodal).
    Uses Gemini API (Text + Vision) to plan the next best action.
    """
    
    def __init__(self):
        self.system_prompt = """You are an autonomous web-agent architect. Your task is to navigate the web to achieve the user's goal.
You are given the user's goal, the current URL, the result of the previous action, AND A SCREENSHOT of the current page.

### CRITICAL VISION ANALYSIS
- Look at the screenshot FIRST.
- Is there a cookie banner, popup, or overlay blocking the view? If yes, your PRIORITY is to dismiss it (CLICK 'Accept', 'Agree', 'Close', 'Reject').
- Is there a search bar visible? If so, target it visually if DOM scraping failed.
- Are there clear buttons or links related to the goal?

### TOOLS
1. 'DOM_SCRAPE': Use this for standard navigation or extracting text if the page looks clean.
2. 'VISION_CLICK': Use this if:
   - You see a cookie banner/popup (e.g. "Alle akzeptieren", "I agree").
   - You need to type into a search bar that DOM scraping missed.
   - The page is a complex Single Page App (SPA).
   - The previous DOM action failed.

### RESPONSE FORMAT (JSON)
{
  "thought_process": "Analyze the screenshot. Is a popup blocking me? What failed last time? Why is this the best next step?",
  "next_action": "GOTO_URL" | "SEARCH" | "CLICK" | "EXTRACT" | "FINISH",
  "tool_preference": "DOM_SCRAPE" | "VISION_CLICK",
  "target": "The exact text on the button/link (for CLICK), the search query (for SEARCH), or the URL (for GOTO_URL)",
  "expected_result": "What should the state look like after this action succeeds?"
}
"""

    def plan_next_step(self, goal: str, current_state: Dict[str, Any], screenshot_bytes: bytes = None) -> Dict[str, Any]:
        """
        Calls Gemini to get the next step in JSON format, including visual context.
        """
        logger.info(f"[Planner] Planning next step for goal: '{goal}'")
        
        prompt_text = f"""{self.system_prompt}

### CURRENT CONTEXT
User Goal: {goal}
Current URL: {current_state.get('url', 'None')}
Last Action Result: {current_state.get('last_action_result', 'None')}

### INSTRUCTION
Look at the screenshot below. What is the single best next step to move closer to the goal?
"""
        prompt_parts = [prompt_text]
        
        # Add screenshot if available
        if screenshot_bytes:
            from PIL import Image
            import io
            image = Image.open(io.BytesIO(screenshot_bytes))
            prompt_parts.append(image)
        else:
            prompt_parts.append("\n[No Screenshot Available - Relying on Text Context]")

        try:
            # Add safety settings
            from google.generativeai.types import HarmCategory, HarmBlockThreshold
            safety_settings = {
                HarmCategory.HARM_CATEGORY_HARASSMENT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_HATE_SPEECH: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_SEXUALLY_EXPLICIT: HarmBlockThreshold.BLOCK_NONE,
                HarmCategory.HARM_CATEGORY_DANGEROUS_CONTENT: HarmBlockThreshold.BLOCK_NONE,
            }

            response = generate_content_with_key_rotation(
                prompt_parts=prompt_parts,
                generation_config={"response_mime_type": "application/json"},
                safety_settings=safety_settings
            )
            
            if not response.parts:
                logger.warning(f"[Planner] Gemini returned no parts. Finish reason: {response.candidates[0].finish_reason}")
                return {
                    "thought_process": "AI returned empty response. Retrying safely.",
                    "next_action": "GOTO_URL", 
                    "tool_preference": "DOM_SCRAPE",
                    "target": "https://www.google.com", 
                    "expected_result": "Reset"
                }

            plan_json_str = response.text.strip()
            # Clean up potential markdown formatting (```json ... ```)
            if plan_json_str.startswith("```json"):
                plan_json_str = plan_json_str[7:-3].strip()
            elif plan_json_str.startswith("```"):
                plan_json_str = plan_json_str[3:-3].strip()

            plan = json.loads(plan_json_str)
            logger.info(f"[Planner] Decided: {plan.get('next_action')} ({plan.get('tool_preference')}) -> {plan.get('target')}")
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
