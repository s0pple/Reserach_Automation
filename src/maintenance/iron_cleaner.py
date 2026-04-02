import os
import glob
import json
from datetime import datetime

# ARE Maintenance: Proactive Iron Fortress Cleanup
PATHS = {
    "locks": r"C:\Users\olive\.openclaw\agents\main\sessions\*.lock",
    "tasks_running": "tasks/running/*.json",
    "tasks_pending": "tasks/pending/*.json",
    "session_data": r"C:\Users\olive\.openclaw\agents\main\sessions\*.jsonl"
}

def cleanup():
    print(f"🧹 [Iron-Cleaner] Starting deep cleaning... {datetime.now().isoformat()}")
    
    # 1. Remove Stalock Files (The root of FailoverErrors)
    locks = glob.glob(PATHS["locks"])
    for l in locks:
        try:
            os.remove(l)
            print(f"   🗑️  CLEARED LOCK: {os.path.basename(l)}")
        except Exception as e:
            print(f"   ❌ Failed to clear lock {l}: {e}")

    # 2. Reset Zombie JSON Tasks (Move back to failed/completed or just delete if corrupted)
    running = glob.glob(PATHS["tasks_running"])
    for r in running:
        try:
            # We move them to completed with a 'REAPED' status
            dest = r.replace("running", "completed")
            os.rename(r, dest)
            print(f"   📦 REAPED ZOMBIE TASK: {os.path.basename(r)}")
        except Exception as e:
            print(f"   ❌ Failed to reap {r}: {e}")

    print("✅ [Iron-Cleaner] System is now DE-PRESSURIZED. Ready for Cold Start.")

if __name__ == "__main__":
    cleanup()
