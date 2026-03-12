import logging
import uuid
from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.venture_state import VentureState, OpportunityNode, IdeaCluster, SignalStrength
from src.core.llm import OpenAIClient

logger = logging.getLogger(__name__)

class GraphBuilder(BaseAgent):
    """
    The Refinery. Synthesizes EvidenceClaims into 'Gold Bar' OpportunityNodes.
    """
    def __init__(self, name: str = "GraphBuilder"):
        super().__init__(name)
        self.llm = OpenAIClient()

    async def process(self, state: VentureState) -> VentureState:
        print(f"[{self.name}] Refining {len(state.claims)} claims...")
        if not state.claims: return state

        opportunity_groups = await self._identify_opportunity_groups(state.claims)
        
        for group in opportunity_groups:
            node_id = str(uuid.uuid4())
            claim_ids = group.get("claim_ids", [])
            if not claim_ids and state.claims:
                claim_ids = list(state.claims.keys())
            
            metrics = self._aggregate_claim_signals(claim_ids, state)
            
            node = OpportunityNode(
                id=node_id,
                title=group.get("title", "Unknown Product"),
                description=group.get("description", ""),
                actor=group.get("actor", "Unknown Actor"),
                core_task=group.get("normalized_task", "General Task"),
                claims=claim_ids,
                claim_count=len(claim_ids),
                frequency_score=metrics["frequency_score"],
                wtp_score=metrics["wtp_score"],
                source_diversity=metrics["source_diversity"],
                opportunity_score=self._calculate_venture_score(metrics)
            )
            state.nodes[node_id] = node
            print(f"  [PRODUCT REFINED] {node.title} | Score: {node.opportunity_score:.1f}")

        return state

    async def _identify_opportunity_groups(self, claims: Dict[str, Any]) -> List[Dict[str, Any]]:
        system_prompt = """
        You are a Venture Strategy Engine. Normalize tasks and group claims into Product Opportunities.
        Respond ONLY with a JSON object containing a list 'opportunities'.
        BLUEPRINT:
        {
          "opportunities": [
            { "title": "Product Name", "actor": "Primary Actor", "normalized_task": "Core Task", "description": "short summary", "claim_ids": ["id1", "id2"] }
          ]
        }
        """
        claims_summary = "\n".join([f"ID: {c.id} | Actor: {c.actor} | Problem: {c.problem}" for c in claims.values()])
        response = await self.llm.generate_json(system_prompt, claims_summary)
        return response.get("opportunities", [])

    def _aggregate_claim_signals(self, claim_ids: List[str], state: VentureState) -> Dict[str, Any]:
        # Logik bleibt gleich wie zuvor
        freq_total = 0.0
        wtp_total = 0.0
        sources = set()
        freq_weights = {SignalStrength.LOW: 1.0, SignalStrength.MEDIUM: 2.5, SignalStrength.HIGH: 5.0, SignalStrength.CRITICAL: 8.0}
        wtp_weights = {SignalStrength.LOW: 1.0, SignalStrength.MEDIUM: 3.0, SignalStrength.HIGH: 7.0, SignalStrength.CRITICAL: 10.0}

        for cid in claim_ids:
            claim = state.claims.get(cid)
            if not claim: continue
            freq_total += freq_weights.get(claim.frequency_signal, 1.0)
            wtp_total += wtp_weights.get(claim.willingness_to_pay_signal, 1.0)
            if "://" in claim.source_url: sources.add(claim.source_url.split('/')[2])
            if claim.extraction_reason and "payment" in claim.extraction_reason.lower(): wtp_total += 5.0
        
        count = len(claim_ids)
        return {
            "claim_count": count,
            "frequency_score": freq_total / count if count > 0 else 0,
            "wtp_score": wtp_total / count if count > 0 else 0,
            "source_diversity": len(sources)
        }

    def _calculate_venture_score(self, metrics: Dict[str, Any]) -> float:
        base = metrics["frequency_score"] + metrics["wtp_score"]
        density_multiplier = 1.0 + (min(metrics["claim_count"], 5) - 1) * 0.25
        diversity_bonus = 1.0 + (min(metrics["source_diversity"], 3) - 1) * 0.1
        return base * density_multiplier * diversity_bonus
