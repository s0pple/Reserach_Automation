import uuid
from typing import List, Dict, Any, Optional
from src.schema.research_node import ResearchNode, NodeType, NodeStatus, EvidenceEntry, ConfidenceFactors
from src.schema.source import SourceMetadata
from src.schema.research_state import ResearchState
from src.core.llm import LLMClient

class ResearchIntake:
    """
    Parses unstructured Deep Research outputs into structured ResearchNodes.
    """
    def __init__(self, llm: LLMClient):
        self.llm = llm

    async def import_from_markdown(self, markdown_text: str, state: ResearchState) -> List[str]:
        """
        Parses Markdown research output into nodes and adds them to state.
        Returns a list of created node_ids.
        """
        prompt = f"""
        Extract the key research findings from this report into a structured JSON list of nodes.
        Each node must have:
        - topic: string
        - type: one of [problem, solution, market, trend, competitor, hypothesis]
        - hypothesis: the core claim or fact
        - evidence: a summary of supporting data
        - sources: a list of objects with [title, url, reliability]

        Report Content:
        {markdown_text[:4000]} # Limit for context
        """

        system_prompt = "You are a Research Importer. Extract structured data into JSON only."

        try:
            extraction = await self.llm.generate_json(prompt, system_prompt)
            raw_nodes = extraction if isinstance(extraction, list) else extraction.get("nodes", [])
            
            created_ids = []
            for raw in raw_nodes:
                node_id = str(uuid.uuid4())[:8]
                
                # 1. Create Sources
                sources_data = raw.get("sources", [])
                source_ids = []
                for s in sources_data:
                    sid = str(uuid.uuid5(uuid.NAMESPACE_URL, s.get("url", str(uuid.uuid4()))))[:8]
                    source = SourceMetadata(
                        source_id=sid,
                        title=s.get("title", "Untitled Source"),
                        url=s.get("url"),
                        reliability_score=float(s.get("reliability", 0.7))
                    )
                    state.add_source(source)
                    source_ids.append(sid)

                # 2. Create Node
                node = ResearchNode(
                    node_id=node_id,
                    topic=raw.get("topic", "Extracted Research"),
                    node_type=NodeType(raw.get("type", "hypothesis").lower()),
                    hypothesis=raw.get("hypothesis", ""),
                    iteration=state.current_iteration,
                    status=NodeStatus.VERIFIED,
                    confidence_factors=ConfidenceFactors(
                        source_reliability_avg=0.8,
                        evidence_count=len(source_ids),
                        consistency_score=0.9,
                        critic_score=0.7,
                        composite_score=0.8
                    )
                )
                
                # 3. Add Evidence
                if raw.get("evidence"):
                    node.evidence_list.append(EvidenceEntry(
                        source_id=source_ids[0] if source_ids else "import",
                        raw_content=raw.get("evidence"),
                        summary=raw.get("evidence"),
                        relevance_score=1.0
                    ))
                
                state.add_node(node)
                created_ids.append(node_id)
            
            return created_ids

        except Exception as e:
            print(f"Error importing from Markdown: {e}")
            return []
