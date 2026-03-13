import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import asyncio
import argparse
import sys
import os

# Command Example:
# python run_research.py "analyze vertical farming Switzerland" --deep --iterations=2

from src.schema.research_state import ResearchState
from src.core.orchestrator import Orchestrator
from src.core.llm import MockLLMClient
from src.core.search import DuckDuckGoSearchProvider
from src.modules.browser.provider import BrowserSearchProvider, SimulatedBrowserProvider
from src.modules.browser.intake.importer import ResearchIntake
from src.core.persistence import PersistenceManager

# Import agents
from src.agents.venture_analyst.planner import Planner
from src.agents.venture_analyst.collector import Collector
from src.agents.venture_analyst.analyst import Analyst
from src.agents.venture_analyst.critic import Critic
from src.agents.venture_analyst.synthesis import SynthesisAgent

async def run_research(intent: str, iterations: int, deep: bool, mock: bool = False, resume: bool = False, persona: str = "main"):
    state_file = f"research_state_{persona}.json"

    # Intelligence: MockLLM handles the 'logical' synthesis of REAL browser data
    llm = MockLLMClient() 
    api_search = DuckDuckGoSearchProvider()

    # State Management
    if resume and os.path.exists(state_file):
        print(f"🔄 Resuming research from {state_file}...")
        state = PersistenceManager.load(state_file)
        intent = state.research_intent
    else:
        print(f"🚀 Starting NEW Research: {intent} (Persona: {persona})")
        state = ResearchState(research_intent=intent, max_iterations=iterations)

    # STEP 1: Deep Research (Real Browser Automation)
    # This is the 'Clawdbot' power-mode that fetches high-quality initial data
    if deep and not state.nodes:
        print(f"\n[CLAWDBOT] Initiating real Deep Research session for '{persona}'...")

        if mock:
            print("[CLAWDBOT] 🧪 Mock mode active. Using Simulated Browser.")
            browser = SimulatedBrowserProvider()
        else:
            # We use the specific persona to ensure isolated session/account
            browser = BrowserSearchProvider(headless=False, persona=persona)

        # Execute Automation - This triggers the Gemini 'Deep Research' mode
        raw_report = await browser.trigger_deep_research(
            prompt=intent,
            tool="gemini"
        )

        # STEP 2: Intake Parsing
        # The importer takes the long-form report and breaks it into ResearchNodes
        print("\n[INTAKE] Scraped report received. Converting to ResearchNodes...")
        importer = ResearchIntake(llm)
        node_ids = await importer.import_from_markdown(raw_report, state)
        print(f"✅ Created {len(node_ids)} ResearchNodes from real browser data.")
        PersistenceManager.save(state, state_file)

    # STEP 3: Agent Pipeline (Refinement & Critique)
    print("\n[PIPELINE] Starting refinement loops...")
    
    # In a future update, each agent could have its OWN persona/browser
    pipeline = [
        Planner("Planner", llm),
        Collector("Collector", llm, api_search), # Uses API search for gaps
        Analyst("Analyst", llm),
        Critic("Critic", llm),
        SynthesisAgent("Synthesis", llm)
    ]

    orchestrator = Orchestrator(pipeline, max_iterations=state.max_iterations, state_file=state_file)
    final_state = await orchestrator.run(state)

    # Output Final Result
    print("\n" + "="*60)
    print("🏁 FINAL CONSOLIDATED RESEARCH REPORT")
    print("="*60)
    if final_state.status_summary:
        print(final_state.status_summary)
    else:
        # Generate a quick summary if not present
        print(f"Research on '{intent}' completed with {len(final_state.nodes)} nodes.")
        for node in final_state.nodes.values():
            print(f"- [{node.node_type.value.upper()}] {node.topic}: {node.hypothesis[:100]}...")
    print("="*60)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Zero-Cost Research Automation (Clawdbot Edition)")
    parser.add_argument("intent", type=str, nargs='?', default=None)
    parser.add_argument("--iterations", type=int, default=1)
    parser.add_argument("--deep", action="store_true", help="Launch real browser Deep Research")
    parser.add_argument("--mock", action="store_true", help="Use simulation mode for testing")
    parser.add_argument("--resume", action="store_true", help="Resume previous session")
    parser.add_argument("--persona", type=str, default="main", help="Account profile (e.g., main, critic, strategist)")

    args = parser.parse_args()

    if not args.resume and not args.intent:
        parser.error("intent required unless using --resume")

    try:
        asyncio.run(run_research(args.intent, args.iterations, args.deep, args.mock, args.resume, args.persona))
    except KeyboardInterrupt:
        print("\n[SYSTEM] Research paused by user.")
        sys.exit(0)
    except Exception as e:
        print(f"\n[SYSTEM] ❌ Fatal Error: {e}")
        sys.exit(1)
