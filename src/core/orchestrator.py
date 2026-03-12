import asyncio
import logging
from typing import List, Optional

from src.schema.research_state import ResearchState
from src.schema.research_node import NodeStatus
from src.core.agent import BaseAgent
from src.core.persistence import PersistenceManager

# Configure basic logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Manages the iterative research loop, agent pipeline, and global state.
    """
    def __init__(self, pipeline: List[BaseAgent], max_iterations: int = 3, state_file: str = "research_state.json"):
        self.pipeline = pipeline
        self.max_iterations = max_iterations
        self.state_file = state_file

    async def run(self, initial_state: ResearchState) -> ResearchState:
        """
        Main loop for research iterations.
        """
        state = initial_state
        state.max_iterations = self.max_iterations
        
        print(f"\n[ORCHESTRATOR] Starting Research for: {state.research_intent}")

        for iteration in range(state.current_iteration, self.max_iterations + 1):
            state.current_iteration = iteration
            print(f"\n--- Iteration {iteration}/{self.max_iterations} ---")
            
            # Run each agent in the pipeline
            for agent in self.pipeline:
                print(f"  Executing agent: {agent.name}...")
                state = await agent.process(state)
            
            # Log metrics for this iteration
            self._log_iteration_metrics(state)
            
            # AUTO-SAVE state
            PersistenceManager.save(state, self.state_file)

            # Check for completion
            if self._should_stop(state):
                print("[ORCHESTRATOR] Termination condition met. Stopping research loop.")
                state.is_complete = True
                PersistenceManager.save(state, self.state_file) # Final save
                break
        
        print("\n[ORCHESTRATOR] Research Complete")
        return state

    def _log_iteration_metrics(self, state: ResearchState):
        """
        Displays a summary of the current state.
        """
        total_nodes = len(state.nodes)
        verified = sum(1 for n in state.nodes.values() if n.status == NodeStatus.VERIFIED)
        contradicted = sum(1 for n in state.nodes.values() if n.status == NodeStatus.CONTRADICTED)
        gaps = len(state.knowledge_gaps)
        sources = len(state.sources)

        print(f"  Metrics -> Total: {total_nodes}, Verified: {verified}, Contradicted: {contradicted}, Gaps: {gaps}, Sources: {sources}")

    def _should_stop(self, state: ResearchState) -> bool:
        """
        Determines if we should exit the loop early.
        """
        if not state.knowledge_gaps and state.current_iteration > 1:
            return True
        return False
