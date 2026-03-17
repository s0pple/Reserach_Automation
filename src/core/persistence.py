import json
import os
import sqlite3
from dataclasses import asdict, is_dataclass
from enum import Enum
from datetime import datetime
from typing import Any, List, Optional, Dict

from src.schema.research_state import ResearchState
from src.schema.research_node import ResearchNode, NodeType, NodeStatus, EvidenceEntry, ConfidenceFactors
from src.schema.source import SourceMetadata

class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    KILLED = "KILLED"

class JobRegistry:
    """
    Manages background jobs in a SQLite database for Phalanx 2.0.
    """
    def __init__(self, db_path: str = "data/jobs.sqlite"):
        # Resolve absolute path to avoid issues with different working directories
        self.db_path = os.path.abspath(db_path)
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS jobs (
                    job_id TEXT PRIMARY KEY,
                    topic TEXT,
                    status TEXT,
                    display TEXT,
                    pid INTEGER,
                    start_time TEXT,
                    end_time TEXT,
                    log_path TEXT,
                    error_msg TEXT
                )
            """)
            conn.commit()

    def register_job(self, job_id: str, topic: str, display: str, log_path: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO jobs (job_id, topic, status, display, start_time, log_path) VALUES (?, ?, ?, ?, ?, ?)",
                (job_id, topic, JobStatus.PENDING.value, display, datetime.now().isoformat(), log_path)
            )

    def update_job(self, job_id: str, **kwargs):
        if not kwargs:
            return
        fields = ", ".join([f"{k} = ?" for k in kwargs.keys()])
        values = list(kwargs.values()) + [job_id]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(f"UPDATE jobs SET {fields} WHERE job_id = ?", values)

    def get_job(self, job_id: str) -> Optional[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute("SELECT * FROM jobs WHERE job_id = ?", (job_id,)).fetchone()
            return dict(row) if row else None

    def get_active_jobs(self) -> List[Dict]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute("SELECT * FROM jobs WHERE status IN (?, ?)", 
                             (JobStatus.PENDING.value, JobStatus.RUNNING.value)).fetchall()
            return [dict(r) for r in rows]

    def cleanup_old_jobs(self, hours: int = 24):
        # Placeholder for future cleanup logic
        pass

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
