import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import argparse
import sys
import os
import json
from rich.console import Console
from rich.table import Table

from src.core.llm import MockLLMClient, OpenAIClient
from src.modules.browser.google_ai_provider import GoogleAIProvider
from src.modules.browser.intake.importer import ResearchIntake
from src.schema.research_state import ResearchState
from src.core.persistence import PersistenceManager

console = Console()

PERSONAS = {
    "Critic": {
        "prompt": "You are an extremely ruthless critic. Find every contradiction, risk, unrealistic claim, bias and weakness in the following research text.",
        "color": "red"
    },
    "Optimist": {
        "prompt": "You are a highly optimistic strategist. Highlight every opportunity, growth potential, positive angle and future-proof advantage in the research.",
        "color": "green"
    },
    "Realist": {
        "prompt": "You are a pragmatic realist. Evaluate the feasibility, estimated costs, timeline and practical next steps for the business model mentioned.",
        "color": "blue"
    },
    "Mediator": {
        "prompt": "Synthesize the previous opinions and the raw data into balanced conclusions. Suggest the next critical research query to close the most important gap.",
        "color": "magenta"
    }
}

async def persona_research_loop(goal: str, iterations: int = 4, headless: bool = False):
    console.rule(f"[bold cyan]CLAWDBOT: Personality-Driven Research Loop[/bold cyan]")
    console.print(f"🎯 [bold]Goal:[/bold] {goal}\n")
    
    # Setup State & Tools
    state = ResearchState(research_intent=goal, max_iterations=iterations)
    llm = OpenAIClient() if os.getenv("OPENAI_API_KEY") else MockLLMClient()
    browser_ai = GoogleAIProvider(headless=headless, persona="research_master")
    importer = ResearchIntake(llm)
    
    current_query = goal
    cycle_order = ["Critic", "Optimist", "Realist", "Mediator"]
    
    for iteration in range(1, iterations + 1):
        persona_key = cycle_order[(iteration - 1) % len(cycle_order)]
        persona = PERSONAS[persona_key]
        
        console.rule(f"[bold {persona['color']}]Iteration {iteration}: Role [{persona_key.upper()}][/bold {persona['color']}]")
        
        # 1. FETCH DATA (Google AI Mode)
        console.print(f"🔍 [bold yellow]Searching Google AI Mode for:[/bold yellow] {current_query}")
        raw_overview = await browser_ai.search_and_extract(current_query)
        
        console.print(f"📄 [GoogleAI] Extracted AI Overview ({len(raw_overview)} characters)")
        
        # 2. PERSONA ANALYSIS
        console.print(f"🧠 [Persona:{persona_key}] Analyzing research content...")
        persona_feedback = await llm.generate(
            prompt=f"Research Text:\n{raw_overview}\n\nTask: {persona['prompt']}",
            system_prompt=persona['prompt']
        )
        
        console.print(f"💬 [bold {persona['color']}]→ Feedback ({len(persona_feedback)} chars):[/bold {persona['color']}]")
        console.print(f"[italic]{persona_feedback[:500]}...[/italic]")

        # 3. IMPORT TO GRAPH
        console.print(f"🕸️ [Importer] Converting findings into ResearchNodes...")
        # Use importer to parse the raw overview into the state
        new_node_ids = await importer.import_from_markdown(raw_overview + "\n\n" + persona_feedback, state)
        console.print(f"✅ Added {len(new_node_ids)} new nodes to research_state.json")
        PersistenceManager.save(state, "research_state.json")

        # 4. FEEDBACK LOOP: Formulate next query
        if persona_key == "Mediator":
            console.print("🔄 [Mediator] Planning next strategic search...")
            next_step_plan = await llm.generate(
                prompt=f"Goal: {goal}\nContext: {raw_overview}\nFeedback: {persona_feedback}\nTask: Suggest the next SEARCH query.",
                system_prompt="Return ONLY 'SEARCH: [query]'"
            )
            if "SEARCH:" in next_step_plan:
                current_query = next_step_plan.split("SEARCH:")[-1].strip()
            else:
                current_query = f"{goal} deep dive {iteration}"
        else:
            # For non-mediators, we use the critique/feedback to sharpen the search
            current_query = f"contradictions and risks in {goal} Switzerland" if persona_key == "Critic" else current_query
            current_query = f"future market growth and tech trends in {goal}" if persona_key == "Optimist" else current_query

    console.rule("[bold cyan]Persona Loop Complete[/bold cyan]")
    
    # Final Table Summary
    table = Table(title="Final Research Summary")
    table.add_column("Topic", style="cyan")
    table.add_column("Type", style="magenta")
    table.add_column("Status", style="green")
    
    for node in state.nodes.values():
        table.add_row(node.topic, node.node_type.value, node.status.value)
    
    console.print(table)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zero-Cost Persona Research Loop")
    parser.add_argument("goal", type=str, help="The research intent")
    parser.add_argument("--iterations", type=int, default=4, help="Number of persona cycles")
    parser.add_argument("--visible", action="store_true", help="Run browser visibly")
    
    args = parser.parse_args()
    
    try:
        asyncio.run(persona_research_loop(args.goal, args.iterations, not args.visible))
    except KeyboardInterrupt:
        console.print("\n[red]Research aborted.[/red]")
        sys.exit(0)
