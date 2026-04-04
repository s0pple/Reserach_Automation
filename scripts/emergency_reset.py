import os
import subprocess
import json

# Paths
BASE_DIR = r"e:\TEST_SYNC\10_projekte_dashboard\10.1_aktiv\Research_Automation"
PENDING_DIR = os.path.join(BASE_DIR, "tasks_v2", "pending")
RUNNING_DIR = os.path.join(BASE_DIR, "tasks_v2", "running")
CONTAINER_NAME = "mcp_gemini_1"

def reset_all():
    print("--- EMERGENCY RESET STARTING ---")
    
    # 1. Kill local worker processes if any (this script is outside)
    # 2. Kill container processes
    print(f"Killing openclaw.mjs in {CONTAINER_NAME}...")
    subprocess.run(["docker", "exec", CONTAINER_NAME, "pkill", "-f", "openclaw.mjs"], capture_output=True)
    
    # 3. Move running tasks back to pending
    if os.path.exists(RUNNING_DIR):
        for filename in os.listdir(RUNNING_DIR):
            if filename.endswith(".json"):
                src = os.path.join(RUNNING_DIR, filename)
                dst = os.path.join(PENDING_DIR, filename)
                print(f"Resetting task: {filename}")
                
                with open(src, "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                data["status"] = "pending"
                data["errors"] = "Emergency Reset: Manual trigger"
                
                with open(dst, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=4)
                
                os.remove(src)
                
                # Also remove log file
                log_file = src.replace(".json", "_raw.log")
                if os.path.exists(log_file):
                    try:
                        os.remove(log_file)
                    except PermissionError:
                        print(f"[WARN] Could not remove log file {log_file} (Process Lock).")

    print("--- EMERGENCY RESET COMPLETE ---")

if __name__ == "__main__":
    reset_all()
