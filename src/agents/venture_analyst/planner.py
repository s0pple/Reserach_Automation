import uuid
import json
from typing import List, Dict, Any, Optional
from src.core.agent import BaseAgent
from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, NodeType, NodeStatus
from src.core.llm import LLMClient

class Planner(BaseAgent):
    """
    Agent responsible for breaking down research intent into structured nodes.
    It identifies key topics, hypotheses, and initial research directions.
    """
    
    def __init__(self, name: str, llm: LLMClient):
        super().__init__(name, llm)

    async def process(self, state: ResearchState) -> ResearchState:
        if state.current_iteration == 1:
            # First pass: Generate initial research structure
            prompt = self._build_initial_prompt(state.research_intent)
        else:
            # Subsequent passes: Focus on filling knowledge gaps
            if not state.knowledge_gaps:
                return state
            prompt = self._build_gap_prompt(state.knowledge_gaps)

        system_prompt = (
            "You are a Senior Research Architect. Your task is to decompose a research goal "
            "into specific, testable ResearchNodes. Return ONLY a JSON object."
        )

        try:
            response_json = await self.llm.generate_json(prompt, system_prompt)
            validated_nodes = self._validate_and_map_nodes(response_json, state.current_iteration)
            
            for node in validated_nodes:
                state.add_node(node)
                
            # Clear gaps if we are in iteration > 1
            if state.current_iteration > 1:
                state.knowledge_gaps = []
                
        except Exception as e:
            # In a real system, we might retry or log a specific error node
            print(f"Error in Planner agent: {e}")
            
        return state

    def _build_initial_prompt(self, intent: str) -> str:
        return f"""
        Research Intent: {intent}

        Decompose this intent into 3-5 initial research nodes. 
        Each node must have:
        - topic: short string
        - type: one of [problem, solution, market, trend, competitor, hypothesis]
        - hypothesis: a testable statement related to the topic

        Response Format:
        {{
            "nodes": [
                {{"topic": "...", "type": "...", "hypothesis": "..."}},
                ...
            ]
        }}
        """

    def _build_gap_prompt(self, gaps: List[str]) -> str:
        gaps_str = "\n".join([f"- {g}" for g in gaps])
        return f"""
        We have identified the following knowledge gaps in our research:
        {gaps_str}

        Create new ResearchNodes to address these specific gaps.
        Each node must have:
        - topic: short string
        - type: one of [problem, solution, market, trend, competitor, hypothesis]
        - hypothesis: a testable statement to investigate the gap

        Response Format:
        {{
            "nodes": [
                {{"topic": "...", "type": "...", "hypothesis": "..."}},
                ...
            ]
        }}
        """

    def _validate_and_map_nodes(self, data: Any, iteration: int) -> List[ResearchNode]:
        """
        Validates the raw LLM JSON and converts it into ResearchNode objects.
        """
        nodes = []
        
        # Handle cases where LLM returns a list directly or a dict with "nodes"
        if isinstance(data, list):
            raw_nodes = data
        elif isinstance(data, dict):
            raw_nodes = data.get("nodes", [])
        else:
            raise ValueError(f"Unexpected LLM response format: {type(data)}")

        valid_types = {t.value for t in NodeType}

        for raw in raw_nodes:
            if not isinstance(raw, dict): continue

            # Basic structural validation
            topic = raw.get("topic")
            node_type_str = raw.get("type", "hypothesis").lower()
            hypothesis = raw.get("hypothesis")

            if not topic or not hypothesis:
                continue # Skip malformed entries
            
            # Map type safely
            if node_type_str not in valid_types:
                node_type = NodeType.HYPOTHESIS
            else:
                node_type = NodeType(node_type_str)

            node = ResearchNode(
                node_id=str(uuid.uuid4())[:8],
                topic=topic,
                node_type=node_type,
                hypothesis=hypothesis,
                iteration=iteration,
                status=NodeStatus.HYPOTHESIS
            )
            nodes.append(node)

        return nodes
