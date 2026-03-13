import asyncio
from src.schema.research_state import ResearchState
from src.core.llm import MockLLMClient
from src.modules.browser.intake.importer import ResearchIntake
from src.modules.browser.provider import SimulatedBrowserProvider

async def test_full_browser_automation_loop():
    print("🚀 Integration Test: Browser Automation -> Research Intake...")
    
    llm = MockLLMClient()
    importer = ResearchIntake(llm)
    browser = SimulatedBrowserProvider(headless=True)
    state = ResearchState("Modular Fusion Costs")

    # 1. Trigger "Deep Research" (Simulated)
    print("  [Step 1] Triggering Browser Automation for Deep Research...")
    raw_report = await browser.trigger_deep_research(
        "Generate a deep report on the LCOE of Small Modular Fusion reactors by 2040.",
        tool="gemini"
    )
    
    # 2. Extract into structured nodes
    print("  [Step 2] Importing into Knowledge Graph...")
    node_ids = await importer.import_from_markdown(raw_report, state)

    # 3. Validation
    print(f"\n--- 🔍 Results ---")
    print(f"✅ Created {len(node_ids)} ResearchNodes from Browser Output.")
    
    for nid in node_ids:
        node = state.nodes[nid]
        print(f"• [{node.node_type.upper()}] {node.topic}")
        print(f"  Hypothesis: {node.hypothesis}")
        
    # Check if sources were also imported
    print(f"✅ Total Sources in Graph: {len(state.sources)}")

    # 4. Example call for real local machine (commented out)
    """
    # To run this on your Windows machine with real Playwright:
    from src.modules.browser.provider import BrowserSearchProvider
    real_browser = BrowserSearchProvider(headless=False, user_data_dir="C:\\Users\\YourName\\ResearchBotSession")
    report = await real_browser.trigger_deep_research("Deep Research Query", tool="gemini")
    print(report)
    """

if __name__ == "__main__":
    asyncio.run(test_full_browser_automation_loop())
