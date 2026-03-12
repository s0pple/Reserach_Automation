import logging
from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.venture_state import VentureState, OpportunityNode, StrategicOption, StrategyRisk
from src.core.llm import OpenAIClient

logger = logging.getLogger(__name__)

class SkepticAgent(BaseAgent):
    """
    The Stress Tester. Attacks strategies.
    """
    def __init__(self, name: str = "SkepticAgent"):
        super().__init__(name)
        self.llm = OpenAIClient()

    async def process(self, state: VentureState) -> VentureState:
        print(f"[{self.name}] Stress-testing {len(state.nodes)} nodes...")
        for node_id, node in state.nodes.items():
            for strategy in node.strategies:
                critique = await self._attack_strategy(node, strategy)
                strategy.risks = [StrategyRisk(**r) for r in critique.get("risks", [])]
                strategy.kill_score = critique.get("kill_score", 0.0)
                strategy.skeptic_verdict = critique.get("verdict", "Unknown")
                node.opportunity_score -= (strategy.kill_score * 0.5)
        return state

    async def _attack_strategy(self, node: OpportunityNode, strategy: StrategicOption) -> Dict[str, Any]:
        system_prompt = """
        You are a Ruthless VC Skeptic. Attack on Incumbent Reaction, Distribution, and Switching Costs.
        Respond ONLY with a JSON object.
        BLUEPRINT:
        {
          "risks": [ { "vector": "Incumbent Reaction", "critique": "...", "severity": "high" } ],
          "kill_score": 8.5,
          "verdict": "DOA"
        }
        """
        user_prompt = f"Strategy: {strategy.title} Logic: {strategy.rationale}"
        return await self.llm.generate_json(system_prompt, user_prompt)
