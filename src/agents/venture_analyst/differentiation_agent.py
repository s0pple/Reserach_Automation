import logging
from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.venture_state import VentureState, OpportunityNode, StrategicOption
from src.core.llm import OpenAIClient

logger = logging.getLogger(__name__)

class DifferentiationAgent(BaseAgent):
    """
    The Strategy Engine. Generates winning product strategies.
    """
    def __init__(self, name: str = "DifferentiationAgent"):
        super().__init__(name)
        self.llm = OpenAIClient()

    async def process(self, state: VentureState) -> VentureState:
        print(f"[{self.name}] Designing strategies for {len(state.nodes)} nodes...")
        for node_id, node in state.nodes.items():
            strategies_json = await self._generate_strategies_for_node(node)
            node.strategies = [StrategicOption(**s) for s in strategies_json]
        return state

    async def _generate_strategies_for_node(self, node: OpportunityNode) -> List[Dict[str, Any]]:
        system_prompt = """
        You are a Senior Venture Architect. Generate 3 DIVERSE winning strategies.
        Respond ONLY with a JSON object containing a list 'strategies'.
        BLUEPRINT:
        {
          "strategies": [
            { "title": "X", "description": "...", "strategy_type": "Verticalization", "rationale": "...", "implementation_difficulty": "medium", "potential_moat": "..." }
          ]
        }
        """
        user_prompt = f"Gap: {node.gap_description} History: {node.strategic_insight}"
        response = await self.llm.generate_json(system_prompt, user_prompt)
        return response.get("strategies", [])
