import os
import json
import enum
import time
import logging
from dataclasses import dataclass, field, asdict
from typing import List, Optional

class Milestone(enum.Enum):
    INITIALIZING = "initializing"
    PAGE_LOADED = "page_loaded"
    PROMPT_INJECTED = "prompt_injected"
    GENERATION_STARTED = "generation_started"
    COMPLETED = "completed"
    FATAL_ERROR = "fatal_error"

@dataclass
class SessionState:
    session_id: str
    request_id: str = "N/A"
    current_goal: str = ""
    current_milestone: Milestone = Milestone.INITIALIZING
    last_stable_url: str = "https://aistudio.google.com/app/prompts/new_chat"
    completed_milestones: List[str] = field(default_factory=list)
    retry_count: int = 0
    max_retries_per_milestone: int = 5
    last_action_timestamp: float = field(default_factory=time.time)
    last_milestone_timestamp: float = field(default_factory=time.time)
    plan_d_triggered: bool = False
    last_oracle_strategy: str = ""
    last_update: float = field(default_factory=time.time)
    metadata: dict = field(default_factory=dict)

    def to_dict(self):
        d = asdict(self)
        d['current_milestone'] = self.current_milestone.value
        return d

    @classmethod
    def from_dict(cls, data: dict):
        # Convert string back to Enum
        if 'current_milestone' in data:
            data['current_milestone'] = Milestone(data['current_milestone'])
        return cls(**data)

class StateManager:
    def __init__(self, data_dir: str = "data/session_states"):
        self.data_dir = data_dir
        os.makedirs(self.data_dir, exist_ok=True)
        self.logger = logging.getLogger("RatchetStateManager")

    def _get_path(self, session_id: str) -> str:
        return os.path.join(self.data_dir, f"{session_id}.json")

    def save_state(self, state: SessionState):
        path = self._get_path(state.session_id)
        state.last_update = time.time()
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(state.to_dict(), f, indent=2, ensure_ascii=False)
            self.logger.info(f"⚓ [Ratchet] State saved for {state.session_id} at milestone: {state.current_milestone.value}")
        except Exception as e:
            self.logger.error(f"❌ [Ratchet] Failed to save state: {e}")

    def load_state(self, session_id: str) -> Optional[SessionState]:
        path = self._get_path(session_id)
        if not os.path.exists(path):
            return None
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return SessionState.from_dict(data)
        except Exception as e:
            self.logger.error(f"❌ [Ratchet] Failed to load state: {e}")
            return None

    def update_milestone(self, session_id: str, milestone: Milestone, url: Optional[str] = None):
        state = self.load_state(session_id)
        if not state:
            state = SessionState(session_id=session_id)
        
        if state.current_milestone != milestone:
            state.current_milestone = milestone
            state.retry_count = 0  # Reset retries on progress
            if milestone.value not in state.completed_milestones:
                state.completed_milestones.append(milestone.value)
        
        if url:
            state.last_stable_url = url
            
        self.save_state(state)

    def increment_retry(self, session_id: str) -> int:
        state = self.load_state(session_id)
        if state:
            state.retry_count += 1
            if state.retry_count >= state.max_retries_per_milestone:
                state.current_milestone = Milestone.FATAL_ERROR
                self.logger.critical(f"🚨 [Ratchet] NOTBREMSE: Max retries ({state.max_retries_per_milestone}) reached for {session_id}")
            self.save_state(state)
            return state.retry_count
        return 0

    def get_reset_level(self, session_id: str) -> str:
        """Determines recovery level: Soft, Med, Hard, or Plan D."""
        state = self.load_state(session_id)
        if not state: return "none"
        
        now = time.time()
        # Stagnation Signals:
        # 1. Milestone Stuck (> 120s)
        stuck_timeout = 120
        is_stuck = (now - state.last_milestone_timestamp) > stuck_timeout
        
        # 2. Same Action Retry threshold
        if state.retry_count >= 3 or (is_stuck and not state.plan_d_triggered):
            return "plan_d"
        elif state.retry_count == 1:
            return "soft"   # Retry action
        elif state.retry_count == 2:
            return "medium" # F5 Reload
        else:
            return "hard"   # Hard Abort / Reset context

    def record_oracle_intervention(self, session_id: str, strategy: str):
        state = self.load_state(session_id)
        if state:
            state.last_oracle_strategy = strategy
            state.plan_d_triggered = True
            self.save_state(state)
            
    def record_action(self, session_id: str):
        state = self.load_state(session_id)
        if state:
            state.last_action_timestamp = time.time()
            self.save_state(state)

    def record_milestone_progress(self, session_id: str):
        state = self.load_state(session_id)
        if state:
            state.last_milestone_timestamp = time.time()
            state.retry_count = 0
            self.save_state(state)
