import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
from src.schema.research_state import ResearchState
from src.core.orchestrator import Orchestrator
from src.agents.venture_analyst.mock_agents import MockPlanner, MockCollector, MockAnalyst, MockCritic, MockGapDetector
from rich.console import Console

console = Console()

async def main():
    # 1. Define Initial Intent
    initial_state = ResearchState(
        research_intent="Analyze the future of AI-driven drug discovery.",
        max_iterations=3
    )

    # 2. Build the Pipeline
    pipeline = [
        MockPlanner("MockPlanner"),
        MockCollector("MockCollector"),
        MockAnalyst("MockAnalyst"),
        MockCritic("MockCritic"),
        MockGapDetector("MockGapDetector")
    ]

    # 3. Initialize Orchestrator
    orchestrator = Orchestrator(pipeline, max_iterations=3)

    # 4. Run the Research
    final_state = await orchestrator.run(initial_state)

    # 5. Review Final State
    console.rule("[bold cyan]Final Summary[/bold cyan]")
    for node_id, node in final_state.nodes.items():
        color = "green" if node.status == "verified" else "red" if node.status == "contradicted" else "yellow"
        console.print(f"[{color}]• [{node.status.upper()}] {node.topic}[/{color}] - Confidence: {node.confidence_factors.composite_score:.2f}")

if __name__ == "__main__":
    asyncio.run(main())
