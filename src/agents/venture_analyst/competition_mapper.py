import logging
from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.venture_state import VentureState, OpportunityNode
from src.core.llm import OpenAIClient

logger = logging.getLogger(__name__)

class CompetitionMapper(BaseAgent):
    """
    The Market Scanner. Identifies incumbents and gaps.
    """
    def __init__(self, name: str = "CompetitionMapper"):
        super().__init__(name)
        self.llm = OpenAIClient()

    async def process(self, state: VentureState) -> VentureState:
        print(f"[{self.name}] Analyzing market for {len(state.nodes)} opportunities...")
        for node_id, node in state.nodes.items():
            mapping = await self._map_competition_for_node(node)
            node.competitors = mapping.get("competitors", [])
            node.weakness_patterns = mapping.get("weakness_patterns", [])
            node.feature_gaps = mapping.get("feature_gaps", [])
            node.gap_description = mapping.get("gap_description", "")
            if node.gap_description: node.opportunity_score += 2.0
        return state

    async def _map_competition_for_node(self, node: OpportunityNode) -> Dict[str, Any]:
        system_prompt = """
        You are a Market Intelligence Expert. Find competitors and weaknesses.
        Respond ONLY with a JSON object.
        BLUEPRINT:
        {
          "competitors": ["Company A", "Company B"],
          "weakness_patterns": ["expensive", "no AI"],
          "feature_gaps": ["missing automation"],
          "gap_description": "why there is a gap"
        }
        """
        user_prompt = f"Opportunity: {node.title} for {node.actor}"
        return await self.llm.generate_json(system_prompt, user_prompt)
