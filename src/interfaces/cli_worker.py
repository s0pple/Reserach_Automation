import os
import json
import time
import subprocess
import glob
import random
from datetime import datetime

# Paths
# INDUSTRIAL HARDENING: Path stability
BASE_DIR = os.path.abspath(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
PROJECT_ROOT = BASE_DIR
TASK_BASE = os.path.join(PROJECT_ROOT, "tasks_v5_clean")
PENDING_DIR = os.path.join(TASK_BASE, "pending_mcp")
RUNNING_DIR = os.path.join(TASK_BASE, "running")
COMPLETED_DIR = os.path.join(TASK_BASE, "completed")
FAILED_DIR = os.path.join(TASK_BASE, "failed")
WORKSPACE_DIR = os.path.join(PROJECT_ROOT, "workspace")
CONTAINER_NAME = "mcp_gemini_1"
TIMEOUT_SECONDS = 900 # Industrial Pacing: 15 mins
OPENCLAW_DIR_CONTAINER = "/app/openclaw-main"

# Import hardening: Add core to sys.path immediately
import sys
sys.path.append(os.path.join(PROJECT_ROOT, "src", "core"))
try:
    from output_validator import validate_file
except ImportError:
    print("[CRIT] [CLI Worker] Failed to import output_validator. Logic will fail.")

# Ensure dirs
for d in [PENDING_DIR, RUNNING_DIR, COMPLETED_DIR, FAILED_DIR]:
    os.makedirs(d, exist_ok=True)

def reap_stale_tasks():
    """Finds all 'running' tasks older than 30 mins and marks them as failed. Cleans up locks."""
    print("[CLEAN] [CLI Worker] Starting Stale Task Cleanup...")
    
    # 1. Clear session locks (Now mapped via volume to host)
    lock_pattern = os.path.expanduser("~/.openclaw/agents/main/sessions/*.lock")
    lock_files = glob.glob(lock_pattern)
    for lf in lock_files:
        try:
            os.remove(lf)
            print(f"   [-] Removed stale lock: {os.path.basename(lf)}")
        except: pass

    # 2. Reap stale 'running' tasks
    files = glob.glob(os.path.join(RUNNING_DIR, "*.json"))
    for file_path in files:
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            
            started_at_str = data.get("started_at")
            if started_at_str:
                started_at = datetime.fromisoformat(started_at_str)
                delta = datetime.now() - started_at
                # If running for more than 15 mins, it's likely a zombie
                if delta.total_seconds() > 900:
                    print(f"   [!] Reaping stale task: {data.get('task_id')} (Running for {int(delta.total_seconds() / 60)}m)")
                    data["status"] = "failed"
                    data["errors"] = "Reaped by Stale Task Reaper: Exceeded 30m timeout."
                    data["finished_at"] = datetime.now().isoformat()
                    
                    # Kill specifically in container
                    subprocess.run(["docker", "exec", CONTAINER_NAME, "pkill", "-f", "openclaw.mjs"], capture_output=True)
                    
                    # Move to completed folder as a failed record
                    target_path = os.path.join(COMPLETED_DIR, os.path.basename(file_path))
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    os.rename(file_path, target_path)
        except Exception as e:
            print(f"   [ERR] Error reaping {file_path}: {e}")
    print("[CLEAN] [CLI Worker] Cleanup complete.")

def get_pending_tasks():
    """Finds all .json files in tasks/pending/."""
    files = glob.glob(os.path.join(PENDING_DIR, "*.json"))
    pending_tasks = []
    
    for file_path in files:
        try:
            # We don't need to load the whole file here, just need the path/mtime
            pending_tasks.append({
                "path": file_path,
                "mtime": os.path.getmtime(file_path)
            })
        except: pass
            
    pending_tasks.sort(key=lambda x: x["mtime"])
    return pending_tasks

def process_task(task_info):
    """Atomic grab, execute, and harvest."""
    pending_path = task_info["path"]
    filename = os.path.basename(pending_path)
    running_path = os.path.join(RUNNING_DIR, filename)
    completed_path = os.path.join(COMPLETED_DIR, filename)

    # 1. ATOMIC GRAB (Concurrency Protection)
    try:
        os.rename(pending_path, running_path)
    except Exception as e:
        # Likely another worker grabbed it first
        return

    # 2. Load and Update Data
    try:
        with open(running_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERR] Failed to read grabbed task {filename}: {e}")
        return

    task_id = data.get("task_id", "unknown")
    prompt = data.get("prompt", "")
    
    # 2.5 CLEAR OLD FAILURE STATE (Avoid State Pollution on retry)
    data["status"] = "running"
    data["started_at"] = datetime.now().isoformat()
    data.pop("errors", None)
    data.pop("exit_code", None)
    data.pop("log_output", None)
    data.pop("output_snippet", None)
    data.pop("finished_at", None)
    
    with open(running_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    print(f"[RUN] [PID {os.getpid()}] Started task: {task_id}", flush=True)

    # 3. Build Command (DOCKER MODE)
    
    try:
        start_time = time.time()
        session_id = data.get("session_id", task_id)
        
        # 2.7 PRE-FLIGHT PURGE (Prevent Phantom-Success)
        expected_result_file = os.path.join(WORKSPACE_DIR, f"result_{task_id}.json")
        if os.path.exists(expected_result_file):
            print(f"[PURGE] [CLI Worker] Removing old result file: {expected_result_file}")
            os.remove(expected_result_file)

        # 3. Build Command (DOCKER MODE)
        
        # We use a list for Popen (NO shell=True) for better signal handling
        # CRITICAL: Update timestamp to prevent immediate stale cleanup
        os.utime(running_path, None)
        
        # Log to file in background
        log_file = os.path.join(RUNNING_DIR, f"{task_id}_raw.log")
        
        # FINAL BRIDGE EXECUTION: Using run_agent.sh
        cmd = [
            "docker", "exec", "-i",
            CONTAINER_NAME,
            "bash", "/app/output/run_agent.sh", task_id, prompt
        ]
        
        print(f"\n[EXE] [CLI Worker] Executing via Docker (ID: {task_id}):")
        print(f"      Command: {' '.join(cmd)}")
        print(f"      Log target: {log_file}\n")
        
        with open(log_file, "w", encoding="utf-8") as f_log:
            f_log.write(f"--- Docker-Exec Run started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f_log.write(f"Task: {task_id}\n")
            f_log.write(f"Container: {CONTAINER_NAME}\n\n")
            f_log.flush()
            
            full_log = ""
            process = subprocess.Popen(
                cmd,
                stdout=f_log,
                stderr=f_log,
                text=True,
                shell=False # CRITICAL: No shell for direct signal passing
            )
            
            try:
                # Poll for completion with timeout (Increased to 900s for research deep-dives)
                process.communicate(timeout=900)
            except subprocess.TimeoutExpired:
                print(f"[TIMEOUT] [CLI Worker] TIMEOUT REACHED (900s). Killing container process...")
                
                # 1. Kill the local docker client
                process.terminate()
                try: process.wait(timeout=5)
                except: process.kill()
                
                # 2. ANTI-ZOMBIE: Kill the actual node process inside the container
                print(f"[KILL] [CLI Worker] Executing Anti-Zombie Kill in {CONTAINER_NAME}...")
                subprocess.run(["docker", "exec", CONTAINER_NAME, "pkill", "-f", "openclaw.mjs"], capture_output=True)
                
                raise RuntimeError("Process timed out (900s).")

        
        # Physical Proof Validation is now handled by output_validator.py in the harvest section.
        pass

    except Exception as e:
        data["status"] = "failed"
        data["errors"] = f"CRITICAL_WORKER_ERROR: {str(e)}"
        data["exit_code"] = 1
        print(f"[CRASH] [CLI Worker] {task_id} CRASHED: {e}")

    # --- LOG HARVESTING ---
    full_log = ""
    try:
        if os.path.exists(log_file):
            with open(log_file, "r", encoding="utf-8", errors="ignore") as f_log:
                full_log = f_log.read()
            
            # Store Full Audit Log
            full_audit_path = os.path.join(COMPLETED_DIR, f"{task_id}.log")
            with open(full_audit_path, "w", encoding="utf-8") as f_audit:
                f_audit.write(full_log)

            MAX_LOG_CHARS = 40000 
            truncated_log = (f"... [TRUNCATED] ...\n" + full_log[-MAX_LOG_CHARS:]) if len(full_log) > MAX_LOG_CHARS else full_log
            data["log_output"] = truncated_log
            data["output_snippet"] = "\n".join(full_log.split("\n")[-10:])
            if 'start_time' in locals():
                data["duration_sec"] = round(time.time() - start_time, 2)
    except Exception as e:
        print(f"[ERR] [CLI Worker] Harvesting failed for {task_id}: {e}")

    # --- DEFINITION OF DONE (DoD) GATE ---
    is_valid_output = False
    val_msg = "Validator Not Attempted"
    
    try:
        print(f"[VAL] [CLI Worker] Deterministic DoD Validation for {task_id}...")
        is_valid_output, val_msg, _ = validate_file(expected_result_file, expected_task_id=task_id)
    except Exception as e:
        val_msg = f"Validator Runtime Crash: {e}"

    is_semantic_failure = ("No reply from agent" in full_log) or ("internal error" in full_log.lower())

    # Final Status Decision (Strict Gate)
    if is_valid_output and not is_semantic_failure:
        data["status"] = "completed"
        data["exit_code"] = 0
        print(f"[OK] [CLI Worker] {task_id} COMPLETED.")
    else:
        data["status"] = "failed"
        # Combine error messages if exists
        current_errors = data.get("errors", "")
        data["errors"] = f"{current_errors} | DoD_FAIL: {val_msg}" if current_errors else f"DoD_FAIL: {val_msg}"
        if is_semantic_failure: data["errors"] += " | SEMANTIC_FAILURE"
        data["exit_code"] = 1
        print(f"[FAIL] [CLI Worker] {task_id} FAILED ({val_msg}).")

    # 4. FINAL MOVE & RETRY LOGIC
    data["finished_at"] = datetime.now().isoformat()
    data["attempts"] = data.get("attempts", 0) + 1
    
    # RE-QUEUE LOGIC (Max 3 attempts total)
    # A task fails if status is NOT 'completed' OR if it has critical errors
    is_actually_successful = (data.get("status") == "completed")
    
    if not is_actually_successful and data["attempts"] < 3:
        print(f"[RETRY] [CLI Worker] Retrying {task_id} (Attempt {data['attempts']+1}/3)...")
        data["status"] = "pending"
        final_target_dir = PENDING_DIR
    else:
        final_target_dir = COMPLETED_DIR

    try:
        with open(running_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4)
        
        # Atomic move to final destination
        final_path = os.path.join(final_target_dir, filename)
        if os.path.exists(final_path):
            os.remove(final_path)
        os.rename(running_path, final_path)
        
        if os.path.exists(log_file):
            os.remove(log_file)
            
    except Exception as e:
        print(f"[CRIT] Critical Error finalizing {task_id}: {e}")

def main_loop():
    print(f"[LISTEN] [CLI Worker] Loop active. Polling {PENDING_DIR}...")
    
    while True:
        tasks = get_pending_tasks()
        if tasks:
            # ARE Phase 2: STRICTLY SEQUENTIAL (1 task per cycle, no pacer)
            target_task = tasks[0]
            print(f"[TRANSITION] [PID {os.getpid()}] PENDING -> RUNNING: {target_task['path']}")
            process_task(target_task)
        else:
            # DEBUG: Why is the queue empty?
            try:
                all_files = os.listdir(PENDING_DIR)
                if all_files:
                    print(f"[DEBUG] [PID {os.getpid()}] Found non-JSON files in pending: {all_files}")
            except: pass
            
            reap_stale_tasks()
            time.sleep(5)

if __name__ == "__main__":
    try:
        reap_stale_tasks()
        main_loop()
    except KeyboardInterrupt:
        print("\n[STOP] [CLI Worker] Stopped by user.")
