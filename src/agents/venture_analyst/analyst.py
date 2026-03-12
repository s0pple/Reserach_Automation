from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, NodeStatus, NodeType
from src.core.llm import LLMClient

class Analyst(BaseAgent):
    """
    Agent responsible for synthesizing evidence into summaries.
    It evaluates the consistency of evidence and updates node status.
    """
    
    def __init__(self, name: str, llm: LLMClient):
        super().__init__(name, llm)

    async def process(self, state: ResearchState) -> ResearchState:
        # Process nodes that have new evidence in this iteration
        target_nodes = [
            node for node in state.nodes.values()
            if node.iteration == state.current_iteration and len(node.evidence_list) > 0
        ]

        for node in target_nodes:
            await self._analyze_node(node, state)
            
        return state

    async def _analyze_node(self, node: ResearchNode, state: ResearchState):
        """
        Summarizes evidence and evaluates the hypothesis.
        """
        evidence_texts = [
            f"Source: {state.sources[ev.source_id].title}\nContent: {ev.raw_content}"
            for ev in node.evidence_list if ev.source_id in state.sources
        ]
        
        if not evidence_texts:
            return

        sep = "-" * 20
        evidence_block = "\n".join(evidence_texts)
        
        prompt = f"""
        Topic: {node.topic}
        Hypothesis: {node.hypothesis}
        
        Collected Evidence:
        {sep}
        {evidence_block}
        {sep}

        Task:
        1. Synthesize the evidence into a concise summary.
        2. Determine if the evidence supports, contradicts, or is neutral towards the hypothesis.
        3. Assign a consistency score (0.0 to 1.0) where 1.0 means all sources strongly agree.

        Return ONLY a JSON object:
        {{
            "summary": "...",
            "verdict": "supported" | "contradicted" | "uncertain",
            "consistency_score": 0.9
        }}
        """

        try:
            analysis = await self.llm.generate_json(prompt, "You are a precise Research Analyst.")
            
            # Update individual evidence entries
            for ev in node.evidence_list:
                if ev.summary == "To be analyzed...":
                    ev.summary = analysis.get("summary", "Analysis failed.")

            # Update Node Status
            verdict = analysis.get("verdict", "uncertain")
            if verdict == "supported":
                node.status = NodeStatus.VERIFIED
            elif verdict == "contradicted":
                node.status = NodeStatus.CONTRADICTED
            else:
                node.status = NodeStatus.HYPOTHESIS

            # Update Confidence Factors
            cf = node.confidence_factors
            cf.consistency_score = float(analysis.get("consistency_score", 0.5))
            cf.evidence_count = len(node.evidence_list)
            
            reliabilities = [
                state.sources[ev.source_id].reliability_score 
                for ev in node.evidence_list if ev.source_id in state.sources
            ]
            if reliabilities:
                cf.source_reliability_avg = sum(reliabilities) / len(reliabilities)

        except Exception as e:
            print(f"Error in Analyst for node {node.topic}: {e}")
