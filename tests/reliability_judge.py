import json
import re
import os

class ReliabilityJudge:
    """The Judge: Parses logs to verify agent causality and resilience."""
    
    def __init__(self, log_path: str):
        self.log_path = log_path
        self.events = []
        self._load_logs()

    def _load_logs(self):
        if not os.path.exists(self.log_path): return
        with open(self.log_path, 'r', encoding='utf-8') as f:
            for line in f:
                if "[EVENT]" in line:
                    match = re.search(r"\{.*\}", line)
                    if match:
                        try: self.events.append(json.loads(match.group(0)))
                        except: pass

    def analyze_run(self):
        """Analyzes the events to reconstruct causality."""
        print(f"⚖️ [Judge] Analyzing Run Log: {self.log_path}...")
        
        decisions = [e for e in self.events if e.get('event') in ['STRATEGY_EXECUTION_START', 'ORACLE_EXECUTION', 'MILESTONE_REACHED', 'ABORT']]
        
        recovered = any(e.get('event') == 'STRATEGY_EXECUTION_START' for e in decisions)
        success = any(e.get('status') == 'success' for e in self.events if e.get('event') == 'TASK_COMPLETED')
        stagnation_triggers = [e for e in self.events if e.get('event') == 'COGNITIVE_SNAPSHOT_START']
        
        print(f"📊 Summary:")
        print(f"   - Success: {'✅' if success else '❌'}")
        print(f"   - Stagnation Triggers: {len(stagnation_triggers)}")
        print(f"   - Recovered Attempt? {'Yes' if recovered else 'No'}")
        
        # Check for Hysteresis (Ping-Pong)
        strategies = [e.get('strategy') for e in self.events if e.get('event') == 'STRATEGY_EXECUTION_START']
        has_hysteresis = len(strategies) != len(set(strategies))
        if has_hysteresis:
            print("🛑 ALERT: Hysteresis Detected! Identical strategies were repeated.")
        
        # Check for ARE Safeties
        latency_detections = [e for e in self.events if "Latency detected" in str(e)]
        if latency_detections:
            print(f"⚖️ [ARE] Safely handled {len(latency_detections)} Latency Illusions.")

        if success and not recovered:
            return "TOTAL_SUCCESS"
        elif success and recovered:
            return "RECOVERED_SUCCESS (Plan D intervened and saved the run)"
        elif not success and has_hysteresis:
            return "CONTROLLED_FAIL (Hysteresis aborted to save tokens)"
        elif not success and len(stagnation_triggers) > 0:
            return "SAFE_FAILURE (Oracle consulted but no solution found)"
        else:
            return "CHAOS_FAILURE (Uncaught exception or silent timeout)"

if __name__ == "__main__":
    import sys
    path = sys.argv[1] if len(sys.argv) > 1 else "proxy.log"
    judge = ReliabilityJudge(path)
    print(f"\nFinal Verdict: {judge.analyze_run()}")
