import asyncio
import json
import os
from src.schema.venture_state import VentureState, SignalStrength
from src.agents.venture_analyst.evidence_extractor import EvidenceExtractor

async def run_suite():
    print("="*60)
    print("Venture Analyst Machine: Domain Test Suite")
    print("="*60)
    
    extractor = EvidenceExtractor()
    fixtures_dir = "tests/fixtures"
    
    summary = []

    for filename in sorted(os.listdir(fixtures_dir)):
        if not filename.endswith(".json"): continue
        
        with open(os.path.join(fixtures_dir, filename), "r") as f:
            suite = json.load(f)
        
        domain = suite["domain"]
        print(f"\n>>> Testing Domain: {domain.upper()}")
        
        for case in suite["test_cases"]:
            state = VentureState(domain=domain)
            raw_data = [{"url": f"test://{case['name']}", "text": case["text"]}]
            
            # Process
            state = await extractor.process(state, raw_data)
            
            # Evaluate
            actual_claims = len(state.claims)
            expected_claims = case["expected_claims"]
            
            success = actual_claims == expected_claims
            
            # If we expected claims, verify actor/problem presence
            if expected_claims > 0 and actual_claims > 0:
                claim = list(state.claims.values())[0]
                if case["expected_actor"].lower() not in claim.actor.lower():
                    success = False
            
            status = "PASS" if success else "FAIL"
            print(f"  - {case['name']}: {status} (Expected: {expected_claims}, Got: {actual_claims})")
            
            summary.append({
                "domain": domain,
                "case": case["name"],
                "status": status
            })

    print("\n" + "="*60)
    print("Test Summary")
    print("="*60)
    print(f"{'Domain':<20} | {'Case':<25} | {'Result'}")
    print("-" * 60)
    for s in summary:
        print(f"{s['domain']:<20} | {s['case']:<25} | {s['status']}")

if __name__ == "__main__":
    asyncio.run(run_suite())
