from dataclasses import dataclass, field
from typing import List, Optional, Dict
from enum import Enum

class NodeType(str, Enum):
    PROBLEM = "problem"
    SOLUTION = "solution"
    MARKET = "market"
    TREND = "trend"
    COMPETITOR = "competitor"
    HYPOTHESIS = "hypothesis"

class NodeStatus(str, Enum):
    HYPOTHESIS = "hypothesis"
    VERIFIED = "verified"
    CONTRADICTED = "contradicted"
    UNKNOWN = "unknown"

@dataclass
class EvidenceEntry:
    source_id: str
    raw_content: str
    summary: str
    relevance_score: float = 0.0

@dataclass
class ConfidenceFactors:
    source_reliability_avg: float = 0.0
    evidence_count: int = 0
    consistency_score: float = 0.0
    critic_score: float = 0.0
    composite_score: float = 0.0

@dataclass
class ResearchNode:
    node_id: str
    topic: str
    node_type: NodeType
    hypothesis: str
    iteration: int = 0
    evidence_list: List[EvidenceEntry] = field(default_factory=list)
    confidence_factors: ConfidenceFactors = field(default_factory=ConfidenceFactors)
    status: NodeStatus = NodeStatus.HYPOTHESIS
    dependencies: List[str] = field(default_factory=list)
    metadata: Dict[str, str] = field(default_factory=dict)
