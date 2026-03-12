import logging
from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.venture_state import VentureState, OpportunityNode, MarketTimingSignal
from src.core.llm import OpenAIClient

logger = logging.getLogger(__name__)

class MarketTimingAgent(BaseAgent):
    """
    The Trend Analyst. Checks if now is the right time.
    """
    def __init__(self, name: str = "MarketTimingAgent"):
        super().__init__(name)
        self.llm = OpenAIClient()

    async def process(self, state: VentureState) -> VentureState:
        print(f"[{self.name}] Analyzing timing for {len(state.nodes)} nodes...")
        for node_id, node in state.nodes.items():
            timing_data = await self._detect_timing_signals_for_node(node)
            node.timing_signals = [MarketTimingSignal(**s) for s in timing_data.get("signals", [])]
            node.timing_verdict = timing_data.get("verdict", "Unknown")
            node.opportunity_score += sum(2.0 for s in node.timing_signals if s.impact_level in ['high', 'transformative'])
        return state

    async def _detect_timing_signals_for_node(self, node: OpportunityNode) -> Dict[str, Any]:
        system_prompt = """
        You are a Market Timing Expert. Detect Tech Shifts, Regulation, and Cost Collapses.
        Respond ONLY with a JSON object.
        BLUEPRINT:
        {
          "signals": [
            { "category": "Tech Shift", "description": "AI reasoning", "impact_level": "high" }
          ],
          "verdict": "Perfect"
        }
        """
        user_prompt = f"Opportunity: {node.title} Constraints: {node.structural_constraints}"
        return await self.llm.generate_json(system_prompt, user_prompt)
