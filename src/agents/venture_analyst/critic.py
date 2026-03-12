from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, NodeStatus
from src.core.llm import LLMClient

class Critic(BaseAgent):
    """
    Agent responsible for challenging the analyst's findings.
    It looks for bias, weak evidence, and logical gaps.
    """
    
    def __init__(self, name: str, llm: LLMClient):
        super().__init__(name, llm)

    async def process(self, state: ResearchState) -> ResearchState:
        # Process nodes that have been analyzed in this iteration
        target_nodes = [
            node for node in state.nodes.values()
            if node.iteration == state.current_iteration and node.status != NodeStatus.HYPOTHESIS
        ]

        for node in target_nodes:
            await self._criticize_node(node, state)
            
        return state

    async def _criticize_node(self, node: ResearchNode, state: ResearchState):
        """
        Evaluates the summary and evidence from a critical perspective.
        """
        evidence_summaries = [ev.summary for ev in node.evidence_list]
        evidence_block = "\n".join([f"- {s}" for s in set(evidence_summaries)])
        
        prompt = f"""
        Topic: {node.topic}
        Hypothesis: {node.hypothesis}
        Analyst Summary: {evidence_summaries[0] if evidence_summaries else "No summary"}
        
        Evidence Base:
        {evidence_block}

        Task:
        1. Critically evaluate if the summary is truly supported by the evidence.
        2. Identify any missing perspectives or potential biases.
        3. Assign a critic_score (0.0 to 1.0) where 1.0 means the conclusion is rock-solid.

        Return ONLY a JSON object:
        {{
            "critique": "...",
            "critic_score": 0.75,
            "suggested_gap": "Optional: a question to resolve the critique"
        }}
        """

        try:
            result = await self.llm.generate_json(prompt, "You are a skeptical Peer Reviewer.")
            
            # Update Confidence Factors
            cf = node.confidence_factors
            cf.critic_score = float(result.get("critic_score", 0.5))
            
            # Calculate composite score (final verification)
            # Formula: Avg(reliability, consistency, critic)
            cf.composite_score = (cf.source_reliability_avg + cf.consistency_score + cf.critic_score) / 3

            # If the critic score is very low, demote the node status
            if cf.critic_score < 0.4:
                node.status = NodeStatus.UNKNOWN
            
            # If the critic suggested a gap, add it to the state
            suggested_gap = result.get("suggested_gap")
            if suggested_gap and len(suggested_gap) > 5:
                state.knowledge_gaps.append(f"Critic Gap: {suggested_gap}")

        except Exception as e:
            print(f"Error in Critic for node {node.topic}: {e}")
