from dataclasses import dataclass, field
from typing import List, Dict
from src.schema.research_node import ResearchNode
from src.schema.source import SourceMetadata

@dataclass
class ResearchState:
    research_intent: str
    current_iteration: int = 1
    max_iterations: int = 3
    nodes: Dict[str, ResearchNode] = field(default_factory=dict)
    sources: Dict[str, SourceMetadata] = field(default_factory=dict)
    knowledge_gaps: List[str] = field(default_factory=list)
    is_complete: bool = False
    status_summary: str = ""

    def add_node(self, node: ResearchNode):
        self.nodes[node.node_id] = node

    def add_source(self, source: SourceMetadata):
        self.sources[source.source_id] = source
