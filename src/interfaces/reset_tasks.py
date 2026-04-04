import os
import shutil
import time

# Final Consolidation Script
SOURCE_DIRS = ["tasks_v1", "tasks_v2", "tasks_v3", "tasks_v4", "tasks_production"]
ARCHIVE_DIR = "tasks_archive"
TARGET_DIR = "tasks_v5_clean"

def reset_infrastructure():
    print("=== INDUSTRIAL RESET INITIATED ===")
    
    # 1. Archive every old folder
    if not os.path.exists(ARCHIVE_DIR):
        os.makedirs(ARCHIVE_DIR)
        
    for d in SOURCE_DIRS:
        if os.path.exists(d):
            new_path = os.path.join(ARCHIVE_DIR, f"{d}_{int(time.time())}")
            print(f"[ARCHIVE] Moving {d} -> {new_path}")
            shutil.move(d, new_path)
            
    # 2. Create fresh target
    print(f"[SETUP] Creating fresh directory: {TARGET_DIR}")
    for sub in ["pending", "running", "completed", "failed"]:
        os.makedirs(os.path.join(TARGET_DIR, sub), exist_ok=True)
        
    # 3. Clean local workspace
    if os.path.exists("workspace"):
        print("[CLEAN] Clearing local workspace files...")
        for f in os.listdir("workspace"):
            if f.endswith(".json") or f.endswith(".log"):
                os.remove(os.path.join("workspace", f))
                
    print("=== RESET COMPLETE. PATH IS NOW: " + TARGET_DIR + " ===")

if __name__ == "__main__":
    reset_infrastructure()
