import os
import shutil
import subprocess
import time
from datetime import datetime

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ARCHIVE_DIR = os.path.join(BASE_DIR, "tasks_archive")
NEW_BASE = os.path.join(BASE_DIR, "tasks_v5_clean")
WORKSPACE_DIR = os.path.join(BASE_DIR, "workspace")
CONTAINER_NAME = "mcp_gemini_1"

def reset_environment():
    print(f"--- [CLEAN UP] Starting Production Reset at {datetime.now().isoformat()} ---")
    
    # 1. Ensure Archive exists
    os.makedirs(ARCHIVE_DIR, exist_ok=True)
    
    # 2. Archive old task folders
    for i in range(1, 5):
        old_folder = os.path.join(BASE_DIR, f"tasks_v{i}")
        if os.path.exists(old_folder):
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            target = os.path.join(ARCHIVE_DIR, f"v{i}_{timestamp}")
            print(f"   [>] Archiving {old_folder} -> {target}")
            shutil.move(old_folder, target)
    
    # 3. Create Fresh Queue
    print(f"   [+] Initializing {NEW_BASE}...")
    for sub in ["pending", "running", "completed", "failed"]:
        os.makedirs(os.path.join(NEW_BASE, sub), exist_ok=True)
    
    # 4. Clear Workspace (Remove old JSON results to avoid validation confusion)
    print(f"   [-] Clearing workspace JSON files...")
    for f in os.listdir(WORKSPACE_DIR):
        if f.endswith(".json"):
            try:
                os.remove(os.path.join(WORKSPACE_DIR, f))
            except: pass

    # 5. Anti-Zombie: Kill hanging processes in container
    print(f"   [!] Killing zombie processes in {CONTAINER_NAME}...")
    try:
        # Kill node and openclaw processes
        subprocess.run(["docker", "exec", CONTAINER_NAME, "pkill", "-f", "node|openclaw"], capture_output=True)
        print("   [OK] Container processes cleared.")
    except Exception as e:
        print(f"   [ERR] Failed to kill container processes: {e}")

    print(f"--- [SUCCESS] Environment is now clinical clean for Phase 5 Run ---")

if __name__ == "__main__":
    reset_environment()
