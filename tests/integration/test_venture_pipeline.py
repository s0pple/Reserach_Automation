import asyncio
import json
from rich.console import Console
from rich.table import Table

from src.schema.venture_state import VentureState, EvidenceClaim, SignalStrength
from src.agents.venture_analyst.evidence_extractor import EvidenceExtractor
from src.agents.venture_analyst.graph_builder import GraphBuilder
from src.agents.venture_analyst.competition_mapper import CompetitionMapper
from src.agents.venture_analyst.historian import Historian
from src.agents.venture_analyst.market_timing_agent import MarketTimingAgent
from src.agents.venture_analyst.differentiation_agent import DifferentiationAgent
from src.agents.venture_analyst.skeptic_agent import SkepticAgent

console = Console()

# --- 1. The Ground Truth Dataset ---
GROUND_TRUTH = [
    {"domain": "property management", "expected_product": "tenant communication automation"},
    {"domain": "property management", "expected_product": "maintenance ticket automation"}
]

# --- 2. The Sample Text ---
SAMPLE_DATA = [
    {
        "url": "https://reddit.com/r/propertymanagement/comments/123",
        "text": "I'm a property manager. Every single morning I wake up to 40 emails about rent and parking. I spend 2 hours daily copy-pasting replies. I'd pay $100/mo for automation."
    },
    {
        "url": "https://g2.com/reviews/property-crm",
        "text": "As a dispatcher, I hate how tenants report issues via SMS and WhatsApp. I lose track of broken pipes constantly."
    }
]

async def run_full_pipeline():
    console.rule("[bold red]Venture Analyst Machine: The Crucible Test[/bold red]")
    
    state = VentureState(domain="property management")
    
    # Initialize Agents
    pipeline = [
        EvidenceExtractor(),
        GraphBuilder(),
        CompetitionMapper(),
        Historian(),
        MarketTimingAgent(),
        DifferentiationAgent(),
        SkepticAgent()
    ]
    
    # Run Pipeline
    for agent in pipeline:
        console.print(f"\n[bold yellow]>>> Executing: {agent.name}[/bold yellow]")
        state = await agent.process(state)
    
    # Step 7: Final Venture Report (The Truth)
    console.rule("[bold green]Final Venture Memos (Post-Crucible)[/bold green]")
    
    sorted_nodes = sorted(state.nodes.values(), key=lambda x: x.opportunity_score, reverse=True)
    
    for node in sorted_nodes:
        console.print(f"\n[bold cyan]OPPORTUNITY: {node.title}[/bold cyan]")
        console.print(f"  Final Adj. Score: [bold yellow]{node.opportunity_score:.1f}[/bold yellow]")
        console.print(f"  Timing: {node.timing_verdict} | Gap: {node.gap_description}")
        
        # Display Strategies with Skeptic Critique
        for s in node.strategies:
            color = "red" if s.kill_score > 7 else "yellow" if s.kill_score > 4 else "green"
            console.print(f"\n  [bold {color}]STRATEGY: {s.title}[/bold {color}] (Kill Score: {s.kill_score}/10)")
            console.print(f"  Verdict: [italic]{s.skeptic_verdict}[/italic]")
            
            risk_table = Table(show_header=True, header_style="bold red", box=None)
            risk_table.add_column("Attack Vector")
            risk_table.add_column("Skeptic's Critique")
            risk_table.add_column("Severity")
            
            for r in s.risks:
                risk_table.add_row(r.vector, r.critique, r.severity)
            console.print(risk_table)
        
        console.print("-" * 60)

if __name__ == "__main__":
    asyncio.run(run_full_pipeline())
