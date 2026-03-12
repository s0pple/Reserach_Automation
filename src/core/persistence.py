import json
import os
from dataclasses import asdict, is_dataclass
from enum import Enum
from datetime import datetime
from typing import Any

from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, NodeType, NodeStatus, EvidenceEntry, ConfidenceFactors
from src.schema.source import SourceMetadata

class ResearchEncoder(json.JSONEncoder):
    """Custom JSON encoder for ResearchState objects."""
    def default(self, obj: Any) -> Any:
        if isinstance(obj, Enum):
            return obj.value
        if isinstance(obj, datetime):
            return obj.isoformat()
        if is_dataclass(obj):
            return asdict(obj)
        return super().default(obj)

class PersistenceManager:
    """
    Handles saving and loading the ResearchState to/from disk.
    """
    @staticmethod
    def save(state: ResearchState, file_path: str = "research_state.json"):
        print(f"  [Persistence] Saving state to {file_path}...")
        data = asdict(state)
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f, cls=ResearchEncoder, indent=2)

    @staticmethod
    def load(file_path: str = "research_state.json") -> ResearchState:
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"No state file found at {file_path}")

        print(f"  [Persistence] Loading state from {file_path}...")
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # 1. Reconstruct Sources
        sources = {
            sid: SourceMetadata(**sdata) 
            for sid, sdata in data.get("sources", {}).items()
        }

        # 2. Reconstruct Nodes
        nodes = {}
        for nid, ndata in data.get("nodes", {}).items():
            # Nested Evidence
            evidence = [EvidenceEntry(**ev) for ev in ndata.pop("evidence_list", [])]
            # Nested Confidence
            confidence = ConfidenceFactors(**ndata.pop("confidence_factors", {}))
            
            # Map strings back to Enums
            ndata["node_type"] = NodeType(ndata["node_type"])
            ndata["status"] = NodeStatus(ndata["status"])
            
            nodes[nid] = ResearchNode(
                evidence_list=evidence,
                confidence_factors=confidence,
                **ndata
            )

        # 3. Create State
        state = ResearchState(
            research_intent=data["research_intent"],
            current_iteration=data["current_iteration"],
            max_iterations=data["max_iterations"],
            nodes=nodes,
            sources=sources,
            knowledge_gaps=data.get("knowledge_gaps", []),
            is_complete=data.get("is_complete", False),
            status_summary=data.get("status_summary", "")
        )
        return state
