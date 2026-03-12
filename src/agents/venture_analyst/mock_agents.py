from src.core.agent import BaseAgent
from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, NodeType, NodeStatus, EvidenceEntry, ConfidenceFactors
from src.schema.source import SourceMetadata
import uuid

class MockAnalyst(BaseAgent):
    async def process(self, state: ResearchState) -> ResearchState:
        for node in state.nodes.values():
            for evidence in node.evidence_list:
                if evidence.summary == "To be analyzed...":
                    evidence.summary = f"Summarized evidence for {node.topic}."
            node.confidence_factors.source_reliability_avg = 0.8
            node.confidence_factors.evidence_count = len(node.evidence_list)
        return state

class MockCritic(BaseAgent):
    async def process(self, state: ResearchState) -> ResearchState:
        for node in state.nodes.values():
            if node.iteration == state.current_iteration:
                node.confidence_factors.critic_score = 0.7
                node.confidence_factors.consistency_score = 0.9
                cf = node.confidence_factors
                cf.composite_score = (cf.source_reliability_avg + cf.critic_score + cf.consistency_score) / 3
                if cf.composite_score > 0.75:
                    node.status = NodeStatus.VERIFIED
        return state

class MockGapDetector(BaseAgent):
    async def process(self, state: ResearchState) -> ResearchState:
        # In iteration 1, we simulate finding a gap to trigger iteration 2
        if state.current_iteration == 1 and not state.knowledge_gaps:
            state.knowledge_gaps.append("What are the regulatory hurdles for fusion?")
        return state
