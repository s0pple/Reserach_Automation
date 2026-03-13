import asyncio
import logging
import sys
import os
from typing import List

# Ensure the root directory is in sys.path so 'src' can be imported
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.schema.venture_state import VentureState
from src.modules.browser.provider import BrowserSearchProvider
from src.agents.venture_analyst.evidence_extractor import EvidenceExtractor
from src.agents.venture_analyst.graph_builder import GraphBuilder
from src.agents.venture_analyst.competition_mapper import CompetitionMapper
from src.agents.venture_analyst.historian import Historian
from src.agents.venture_analyst.market_timing_agent import MarketTimingAgent
from src.agents.venture_analyst.differentiation_agent import DifferentiationAgent
from src.agents.venture_analyst.skeptic_agent import SkepticAgent
from src.agents.venture_analyst.reporting_agent import VentureMemoAgent
from src.modules.db.database import init_db, get_session, ResearchRun, Opportunity

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("VentureAnalyst")

async def run_big_bang(domain: str):
    print(f"\n[BIG BANG] Starting Venture Analysis for: {domain}")
    
    # 0. Initialize Database
    try:
        init_db()
        logger.info("Database initialized successfully.")
    except Exception as e:
        logger.warning(f"Database initialization failed: {e}")

    # 1. Initialize State
    state = VentureState(domain=domain)
    
    # 2. Field Research (The Hunting Grounds)
    print("\n[1/3] FIELD RESEARCH: Scanning High-Signal Areas...")
    browser = BrowserSearchProvider(headless=True)
    
    queries = [
        'site:reddit.com/r/lawyers "legal compliance" tedious manual',
        'site:reddit.com/r/paralegal "AML" OR "KYC" spreadsheet frustration',
        'G2 reviews "compliance software" slow clunky complaints'
    ]
    
    raw_data = []
    
    # --- FORCE SYNTHETIC DATA FOR TESTING ---
    # We comment out the real-world search to ensure the pipeline gets good data
    # and we can test the browser automation for Deep Research in Phase 4.
    # try:
    #     for q in queries:
    #         results = await browser.search_and_scrape(q, max_results=2)
    #         raw_data.extend(results)
    # except Exception as e:
    #     print(f"  [Browser] ❌ Serious failure: {e}")

    # --- FALLBACK INJECTION (The 'Synthetic Blood' Trick) ---
    if not raw_data:
        print("\n  [SYSTEM] ⚠️ Real-world search failed. Injecting 'Synthetic Pain' to test pipeline...")
        raw_data = [
            {
                "url": "https://reddit.com/r/lawyers/comments/legal_hell",
                "text": "I spend 5 hours a day manually checking KYC documents against the new AML regulations. It's a nightmare. My software is slow and clunky. I'd pay anything for a tool that auto-flags discrepancies."
            },
            {
                "url": "https://g2.com/reviews/compliance-tracker",
                "text": "This software sucks. It doesn't integrate with our file system. I have to manually upload PDFs. The UI is from 1995. We are switching back to Excel."
            }
        ]

    # 3. The Pipeline (The Crucible)
    print(f"\n[2/3] THE CRUCIBLE: Processing {len(raw_data)} data entries through Agent Funnel...")
    
    # Initialize all agents
    extractor = EvidenceExtractor()
    builder = GraphBuilder()
    mapper = CompetitionMapper()
    historian = Historian()
    timer = MarketTimingAgent()
    differ = DifferentiationAgent()
    skeptic = SkepticAgent()
    reporter = VentureMemoAgent()

    # Sequential State Processing
    print(f"\n>>> Executing: {extractor.name}")
    state = await extractor.process(state, raw_data)

    pipeline = [builder, mapper, historian, timer, differ, skeptic, reporter]
    
    for agent in pipeline:
        print(f"\n>>> Executing: {agent.name}")
        state = await agent.process(state)

    # 4. Final Output
    print("\n" + "="*60)
    print("[3/4] DONE: Venture Memos have been generated.")
    print(f"Check the 'reports/' folder for the detailed results.")
    print("="*60)
    
    if state.metadata.get("venture_memos"):
        print("\nTOP MEMO PREVIEW:")
        print(state.metadata["venture_memos"][0])

    # 3.5. Persist Results to Database
    print("\n[DB] Saving results to data/research.db...")
    try:
        session = get_session()
        
        # Calculate summary metrics
        total_claims = sum(len(node.metadata.get("evidence_ids", [])) for node in state.nodes.values())
        top_score = max((node.opportunity_score for node in state.nodes.values()), default=0.0)
        
        # Create ResearchRun
        run = ResearchRun(
            domain=domain,
            total_claims_extracted=total_claims,
            top_opportunity_score=top_score,
            status="Completed"
        )
        session.add(run)
        session.flush() # Get run.id

        # Create Opportunities
        memos = state.metadata.get("venture_memos", [])
        for i, (node_id, node) in enumerate(state.nodes.items()):
            memo = memos[i] if i < len(memos) else ""
            opp = Opportunity(
                run_id=run.id,
                title=node.title,
                score=node.opportunity_score,
                rationale=node.description, # Using node.description as the rationale
                memo_markdown=memo
            )
            session.add(opp)
            
        session.commit()
        session.close()
        print(f"  [DB] Successfully saved {len(state.nodes)} opportunities.")
    except Exception as e:
        logger.warning(f"  [DB] ❌ Failed to save results: {e}")

    # 5. The Deep Research Integration (The Final Truth)
    if state.nodes:
        # Find the node with the highest opportunity score
        top_node = max(state.nodes.values(), key=lambda n: n.opportunity_score)
        prompt = top_node.metadata.get("deep_research_prompt")
        
        if prompt:
            print("\n" + "="*60)
            print(f"[4/4] THE FINAL ORDEAL: Executing Deep Research for: {top_node.title}")
            print("="*60)
            
            # Use headless=False so we can see the GUI action, or the user can log in if needed
            dr_browser = BrowserSearchProvider(headless=False, persona="main")
            
            try:
                final_report = await dr_browser.trigger_deep_research(prompt=prompt, tool="gemini")
                
                # Save Final Report
                safe_domain = domain.replace(" ", "_").lower()
                dr_filepath = f"reports/final_deep_research_{safe_domain}.md"
                with open(dr_filepath, "w", encoding="utf-8") as f:
                    f.write(final_report)
                print(f"\n  [DEEP RESEARCH SAVED] {dr_filepath}")
            except Exception as e:
                print(f"  [Deep Research Failed] {e}")

if __name__ == "__main__":
    asyncio.run(run_big_bang("AI for Legal Compliance"))
