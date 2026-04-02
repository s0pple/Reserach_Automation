import os
import json
import time
import subprocess
import glob
import random
from datetime import datetime

# Paths
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
TASKS_DIR = os.path.join(BASE_DIR, "tasks_v1")
PENDING_DIR = os.path.join(TASKS_DIR, "pending")
RUNNING_DIR = os.path.join(TASKS_DIR, "running")
COMPLETED_DIR = os.path.join(TASKS_DIR, "completed")
OPENCLAW_DIR = r"E:\TEST_SYNC\10_projekte_dashboard\10.1_aktiv\openclaw-main\MyClaw\openclaw-main"

# Ensure dirs
for d in [PENDING_DIR, RUNNING_DIR, COMPLETED_DIR]:
    os.makedirs(d, exist_ok=True)

def reap_stale_tasks():
    """Finds all 'running' tasks older than 30 mins and marks them as failed. Cleans up locks."""
    print("🧹 [CLI Worker] Starting Stale Task Cleanup...")
    
    # 1. Clear session locks (Prevent FailoverError)
    lock_pattern = r"C:\Users\olive\.openclaw\agents\main\sessions\*.lock"
    lock_files = glob.glob(lock_pattern)
    for lf in lock_files:
        try:
            os.remove(lf)
            print(f"   🗑️  Removed stale lock: {os.path.basename(lf)}")
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
                # If running for more than 5 mins, it's likely a zombie
                if delta.total_seconds() > 300:
                    print(f"   ⚠️ Reaping stale task: {data.get('task_id')} (Running for {int(delta.total_seconds() / 60)}m)")
                    data["status"] = "failed"
                    data["errors"] = "Reaped by Stale Task Reaper: Exceeded 30m timeout."
                    data["finished_at"] = datetime.now().isoformat()
                    
                    # Move to completed folder as a failed record
                    target_path = os.path.join(COMPLETED_DIR, os.path.basename(file_path))
                    with open(file_path, "w", encoding="utf-8") as f:
                        json.dump(data, f, indent=4)
                    os.rename(file_path, target_path)
        except Exception as e:
            print(f"   ❌ Error reaping {file_path}: {e}")
    print("🧹 [CLI Worker] Cleanup complete.")

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
        print(f"❌ Failed to read grabbed task {filename}: {e}")
        return

    task_id = data.get("task_id", "unknown")
    prompt = data.get("prompt", "")
    data["status"] = "running"
    data["started_at"] = datetime.now().isoformat()
    
    with open(running_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)
    
    print(f"🚀 [CLI Worker] Started task: {task_id}", flush=True)

    # 3. Build Command
    node_path = r"C:\Program Files\nodejs\node.exe"
    config_path = os.path.join(OPENCLAW_DIR, "openclaw.json")
    env = os.environ.copy()
    env["OPENCLAW_CONFIG_PATH"] = config_path
    
    # Absolute log for immediate debugging
    log_file = os.path.join(RUNNING_DIR, f"{task_id}_raw.log")
    
    try:
        start_time = time.time()
        session_id = data.get("session_id", task_id)
        cmd = f'"{node_path}" "{os.path.join(OPENCLAW_DIR, "openclaw.mjs")}" agent --local --agent main --session-id "{session_id}" -m "{prompt}"'
        print(f"🎬 [CLI Worker] Executing: {cmd}")
        
        # Execute with piped output to capture logs
        # We use a context manager for the log file to ensure it's flushed
        with open(log_file, "w") as f_log:
            f_log.write(f"--- Direct Node Run started at {time.strftime('%Y-%m-%d %H:%M:%S')} ---\n")
            f_log.write(f"Task: {task_id}\n\n")
            f_log.flush()
            
            process = subprocess.Popen(
                cmd,
                cwd=OPENCLAW_DIR, 
                env=env,
                stdout=f_log,
                stderr=f_log,
                text=True, 
                shell=True
            )
            
            try:
                # ARE: Hard 5m Polling for Process Tree
                stdout, stderr = process.communicate(timeout=300)
            except subprocess.TimeoutExpired:
                print(f"🛑 [CLI Worker] TIMEOUT REACHED (300s). Killing process tree...")
                # Kill the process and all its children (Shell-Leak-Prevention)
                process.terminate()
                process.wait(timeout=5)
                # Ensure it's dead
                if process.poll() is None:
                    process.kill()
                raise RuntimeError("Process timed out (300s).")
        
        # Log Management: Audit File & JSON Truncation
        with open(log_file, "r", encoding="utf-8", errors="ignore") as f_log:
            full_log = f_log.read()
        
        # 1. Store Full Audit Log separately
        full_audit_path = os.path.join(COMPLETED_DIR, f"{task_id}.log")
        with open(full_audit_path, "w", encoding="utf-8") as f_audit:
            f_audit.write(full_log)

        # 2. Embed Truncated version in JSON (Max ~40KB)
        MAX_LOG_CHARS = 40000 
        if len(full_log) > MAX_LOG_CHARS:
            truncated_log = f"... [TRUNCATED - See {task_id}.log for full history] ...\n" + full_log[-MAX_LOG_CHARS:]
        else:
            truncated_log = full_log

        duration = round(time.time() - start_time, 2)
        data["log_output"] = truncated_log
        data["output_snippet"] = "\n".join(full_log.split("\n")[-10:])
        data["errors"] = ""
        data["duration_sec"] = duration
        data["exit_code"] = process.returncode
        
        # ARE Phase 2.1: Physical Proof Validation
        expected_file = data.get("expected_file")
        expected_content = data.get("expected_content")
        
        output_verified = True
        validation_error = ""
        
        if expected_file:
            # Resolve path relative to BASE_DIR if it's a relative path starting with 'workspace/'
            full_expected_path = os.path.join(BASE_DIR, expected_file)
            if not os.path.exists(full_expected_path):
                output_verified = False
                validation_error = f"Missing expected file: {expected_file}"
            elif expected_content:
                try:
                    with open(full_expected_path, "r", encoding="utf-8") as f_out:
                        actual_content = f_out.read().strip()
                        if expected_content not in actual_content:
                            output_verified = False
                            validation_error = f"Divergent content in {expected_file}"
                except Exception as ve:
                    output_verified = False
                    validation_error = f"Verification error: {ve}"

        # ARE Phase 2: Semantic Validation (Truth in JSON)
        is_semantic_failure = ("No reply from agent" in full_log) or ("internal error" in full_log.lower())
        
        if process.returncode == 0 and not is_semantic_failure and output_verified:
            data["status"] = "completed"
            print(f"✅ [CLI Worker] {task_id} COMPLETED ({duration}s).")
        else:
            data["status"] = "failed"
            failure_reason = validation_error if not output_verified else ("Semantic Failure (No reply/Internal Error)" if is_semantic_failure else f"Exit Code {process.returncode}")
            print(f"❌ [CLI Worker] {task_id} FAILED ({failure_reason}).")

    except Exception as e:
        data["status"] = "failed"
        data["errors"] = str(e)
        print(f"🚨 [CLI Worker] {task_id} CRASHED: {e}")

    # 4. FINAL MOVE & RETRY LOGIC
    data["finished_at"] = datetime.now().isoformat()
    data["attempts"] = data.get("attempts", 0) + 1
    
    # Identify failure (Exit code or Silent failure)
    is_failure = (data.get("exit_code", 0) != 0) or ("No reply from agent" in data.get("log_output", ""))
    
    # RE-QUEUE LOGIC (Max 3 attempts total)
    if is_failure and data["attempts"] < 3:
        print(f"🔄 [CLI Worker] Retrying {task_id} (Attempt {data['attempts']+1}/3)...")
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
        print(f"💥 Critical Error finalizing {task_id}: {e}")

def main_loop():
    print(f"📡 [CLI Worker] Loop active. Polling {PENDING_DIR}...")
    
    while True:
        tasks = get_pending_tasks()
        if tasks:
            # ARE Phase 2: STRICTLY SEQUENTIAL (1 task per cycle, no pacer)
            target_task = tasks[0]
            print(f"🔄 [State Transition] PENDING -> RUNNING: {target_task['path']}")
            process_task(target_task)
        else:
            reap_stale_tasks()
            time.sleep(5)

if __name__ == "__main__":
    try:
        reap_stale_tasks()
        main_loop()
    except KeyboardInterrupt:
        print("\n🛑 [CLI Worker] Stopped by user.")
