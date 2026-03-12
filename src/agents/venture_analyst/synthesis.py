from typing import List, Dict, Any
from src.core.agent import BaseAgent
from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, NodeStatus, NodeType
from src.core.llm import LLMClient

class SynthesisAgent(BaseAgent):
    """
    Final agent in the pipeline. It compiles high-confidence nodes 
    into a structured Markdown report.
    """
    
    def __init__(self, name: str, llm: LLMClient):
        super().__init__(name, llm)

    async def process(self, state: ResearchState) -> ResearchState:
        # Only run synthesis if we are on the last iteration or research is complete
        if state.current_iteration < state.max_iterations and not state.is_complete:
            return state

        print(f"  [{self.name}] Generating final research report...")
        
        # 1. Filter for high-confidence or verified nodes
        relevant_nodes = [
            node for node in state.nodes.values()
            if node.status == NodeStatus.VERIFIED or node.confidence_factors.composite_score > 0.4
        ]

        if not relevant_nodes:
            state.status_summary = "No high-confidence findings were discovered."
            return state

        # 2. Group nodes by type for the LLM
        grouped_data = self._group_nodes(relevant_nodes)
        
        # 3. Generate the report via LLM
        prompt = self._build_synthesis_prompt(state.research_intent, grouped_data)
        
        try:
            report = await self.llm.generate(prompt, "You are a Strategic Research Director.")
            state.status_summary = report
            state.is_complete = True
        except Exception as e:
            print(f"Error in Synthesis: {e}")
            state.status_summary = "Failed to generate final report."

        return state

    def _group_nodes(self, nodes: List[ResearchNode]) -> Dict[str, List[Dict[str, Any]]]:
        groups = {}
        for node in nodes:
            ntype = node.node_type.value
            if ntype not in groups:
                groups[ntype] = []
            
            summary = node.evidence_list[0].summary if node.evidence_list else "No detailed evidence."
            
            groups[ntype].append({
                "topic": node.topic,
                "hypothesis": node.hypothesis,
                "summary": summary,
                "confidence": round(node.confidence_factors.composite_score, 2)
            })
        return groups

    def _build_synthesis_prompt(self, intent: str, groups: Dict[str, Any]) -> str:
        sections = []
        for ntype, items in groups.items():
            item_list = []
            for item in items:
                item_str = (
                    f"### {item['topic']} (Conf: {item['confidence']})\n"
                    f"- **Hypothesis**: {item['hypothesis']}\n"
                    f"- **Finding**: {item['summary']}"
                )
                item_list.append(item_str)
            
            ntype_header = f"## {ntype.upper()}s"
            ntype_content = "\n".join(item_list)
            sections.append(f"{ntype_header}\n{ntype_content}")

        all_sections = "\n\n".join(sections)
        return f"""
        Research Goal: {intent}

        The following findings have been verified across multiple research iterations:

        {all_sections}

        Task:
        Create a professional, executive-level Markdown Research Report.
        Structure:
        1. Executive Summary
        2. Key Opportunities (Ranked)
        3. Critical Risks & Problems
        4. Strategic Recommendations

        Keep it concise, high-signal, and actionable.
        """
