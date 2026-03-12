import asyncio
import os
import json
from src.schema.venture_state import VentureState
from src.agents.venture_analyst.evidence_extractor import EvidenceExtractor

# --- Realistic Field Data (Simulating the 'Beach of Trash') ---
REALISTIC_SAMPLES = [
    {
        "url": "https://reddit.com/r/propertymanagement/thread/1",
        "name": "Mixed Signal / Hype Sandwich",
        "text": """
        AI will revolutionize everything in property management. In 2026, automation will be the standard.
        But honestly, the worst part of my current day is replying to tenant emails every single morning about parking.
        I spend 2 hours just copy-pasting answers. AI could probably help, but right now it's just a manual grind.
        We are entering a new era of technology.
        """
    },
    {
        "url": "https://g2.com/reviews/recruiting-tool",
        "name": "Implicit Actor (Inference)",
        "text": """
        Review: Scheduling interviews takes half my day. Coordinating across timezones is a nightmare.
        I have to check 4 calendars and the candidate's availability manually.
        """
    },
    {
        "url": "https://random-blog.com/ai-future",
        "name": "Pure Noise / Hype",
        "text": """
        The future of work is automated. AI is the most disruptive technology of our time.
        Companies that don't adapt will die. Harness the power of neural networks today.
        """
    }
]

async def run_realistic_test():
    print("="*60)
    print("Venture Analyst Machine: Field Test (Realistic Input)")
    print("="*60)
    
    extractor = EvidenceExtractor()
    state = VentureState(domain="diverse")
    
    await extractor.process(state, REALISTIC_SAMPLES)
    
    print("\n" + "-"*60)
    print("RESULTS & METRICS")
    print("-" * 60)
    print(f"Total Texts Processed: {state.total_processed_texts}")
    print(f"Valid Claims Found:    {len(state.claims)}")
    print(f"Claims Discarded:      {state.discarded_claims_count}")
    
    snr = len(state.claims) / state.total_processed_texts if state.total_processed_texts > 0 else 0
    print(f"Signal-to-Noise Ratio: {snr:.2%}")
    
    print("\n" + "-"*60)
    print("DETAILED CLAIMS (Inference & Reason Check)")
    print("-" * 60)
    for cid, claim in state.claims.items():
        print(f"Actor:     {claim.actor}")
        print(f"Problem:   {claim.problem[:60]}...")
        print(f"Reason:    {claim.extraction_reason}")
        print(f"Signal:    Freq={claim.frequency_signal.value}, WTP={claim.willingness_to_pay_signal.value}")
        print("-" * 30)

    # Sanity Checks
    assert len(state.claims) == 2, f"Expected 2 valid claims, found {len(state.claims)}"
    assert state.discarded_claims_count >= 1, "Should have discarded the hype blog post"
    
    print("\n[SUCCESS] Field test passed. Seismograph is calibrated for the beach.")

if __name__ == "__main__":
    asyncio.run(run_realistic_test())
