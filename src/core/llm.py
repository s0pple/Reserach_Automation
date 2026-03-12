import os
import json
import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any
from src.core.secret import generate_content_with_key_rotation

logger = logging.getLogger(__name__)

class LLMClient(ABC):
    @abstractmethod
    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        pass

class OpenAIClient(LLMClient):
    """
    Alias for Gemini 2.5 Flash Engine with multi-key rotation.
    """
    def __init__(self, model: str = "gemini-2.5-flash"):
        self.model = model

    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        try:
            full_prompt = f"SYSTEM INSTRUCTION: {system_prompt}\n\nUSER INPUT: {user_prompt}\n\nRespond ONLY with valid JSON."
            
            # Execute the rotation logic in a thread to remain async-friendly
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, 
                lambda: generate_content_with_key_rotation(
                    full_prompt,
                    generation_config={"response_mime_type": "application/json", "temperature": 0.2}
                )
            )
            
            return json.loads(response.text)
            
        except Exception as e:
            logger.error(f"[LLM Error] Engine failure: {e}")
            return {"error": str(e), "status": "failed_extraction"}

class MockLLMClient(LLMClient):
    async def generate_json(self, system_prompt: str, user_prompt: str) -> Dict[str, Any]:
        return {"status": "mock"}
