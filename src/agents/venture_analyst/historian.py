import logging
from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.venture_state import VentureState, OpportunityNode
from src.core.llm import OpenAIClient

logger = logging.getLogger(__name__)

class Historian(BaseAgent):
    """
    The Trauma Analyst. Learns from past failures.
    """
    def __init__(self, name: str = "Historian"):
        super().__init__(name)
        self.llm = OpenAIClient()

    async def process(self, state: VentureState) -> VentureState:
        print(f"[{self.name}] Investigating trauma for {len(state.nodes)} nodes...")
        for node_id, node in state.nodes.items():
            history = await self._investigate_history_for_node(node)
            node.historical_attempts = history.get("historical_attempts", [])
            node.failure_patterns = history.get("failure_patterns", [])
            node.structural_constraints = history.get("structural_constraints", [])
            node.strategic_insight = history.get("strategic_insight", "")
        return state

    async def _investigate_history_for_node(self, node: OpportunityNode) -> Dict[str, Any]:
        system_prompt = """
        You are a Venture Historian. Identify dead startups and failure patterns.
        Respond ONLY with a JSON object.
        BLUEPRINT:
        {
          "historical_attempts": ["Startup X"],
          "failure_patterns": ["friction"],
          "structural_constraints": ["legacy data"],
          "strategic_insight": "why it's different now"
        }
        """
        user_prompt = f"Topic: {node.title} for {node.actor}"
        return await self.llm.generate_json(system_prompt, user_prompt)
