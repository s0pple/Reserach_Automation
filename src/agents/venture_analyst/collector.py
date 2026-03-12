import uuid
import asyncio
from typing import List, Dict, Any, Optional
from src.core.agent import BaseAgent
from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, EvidenceEntry, NodeStatus
from src.schema.source import SourceMetadata
from src.core.llm import LLMClient
from src.core.search import SearchProvider

class Collector(BaseAgent):
    """
    Agent responsible for finding evidence. 
    It generates search queries, fetches data, and records sources.
    """
    
    def __init__(self, name: str, llm: LLMClient, search_provider: SearchProvider):
        super().__init__(name, llm)
        self.search_provider = search_provider

    async def process(self, state: ResearchState) -> ResearchState:
        # Collect nodes that need work this iteration
        target_node_ids = [
            node_id for node_id, node in state.nodes.items()
            if node.iteration == state.current_iteration and node.status == NodeStatus.HYPOTHESIS
        ]

        if not target_node_ids:
            return state

        # Process each target node
        tasks = [self._process_node(state, state.nodes[node_id]) for node_id in target_node_ids]
        await asyncio.gather(*tasks)
            
        return state

    async def _process_node(self, state: ResearchState, node: ResearchNode):
        """
        Generates queries and performs search for a single node.
        """
        # 1. Generate 2 search queries using LLM
        prompt = f"""
        Node Topic: {node.topic}
        Hypothesis: {node.hypothesis}

        Generate 2 specific search queries to find evidence that supports or refutes this hypothesis.
        Return ONLY a JSON list of strings.
        Example: ["query 1", "query 2"]
        """
        
        try:
            queries_data = await self.llm.generate_json(prompt, "You are a research assistant.")
            queries = queries_data if isinstance(queries_data, list) else queries_data.get("queries", [])
            
            # 2. Execute search queries
            for query in queries:
                results = await self.search_provider.search(query, max_results=2)
                
                # 3. Add results to state and node
                for result in results:
                    source_id = str(uuid.uuid5(uuid.NAMESPACE_URL, result.url))[:8]
                    
                    # Store source if not already there
                    if source_id not in state.sources:
                        source = SourceMetadata(
                            source_id=source_id,
                            title=result.title,
                            url=result.url,
                            source_type=result.source_type,
                            reliability_score=result.score
                        )
                        state.add_source(source)
                    
                    # Add evidence entry to node
                    evidence = EvidenceEntry(
                        source_id=source_id,
                        raw_content=result.snippet,
                        summary="To be analyzed...",
                        relevance_score=0.5 # Initial score
                    )
                    node.evidence_list.append(evidence)

        except Exception as e:
            print(f"Error in Collector for node {node.topic}: {e}")
