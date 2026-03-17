import asyncio
import os
import sys
import shutil
import signal
import socket
import subprocess
from datetime import datetime
from src.core.persistence import JobRegistry, JobStatus

def find_free_display(start_display=100):
    """Finds the first available X display."""
    display = start_display
    while True:
        # Check for lock file
        if not os.path.exists(f"/tmp/.X{display}-lock"):
            # Also check socket just to be sure
            sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            try:
                sock.connect(f"/tmp/.X11-unix/X{display}")
                sock.close()
            except socket.error:
                return display
        display += 1
        if display > 150: # Safety limit
            raise RuntimeError("No free display found in range 100-150")

async def run_job(job_id: str, topic: str):
    registry = JobRegistry()
    display_num = find_free_display()
    display = f":{display_num}"
    job_dir = os.path.abspath(f"temp/jobs/{job_id}")
    profile_dir = os.path.join(job_dir, "profile")
    log_path = os.path.join(job_dir, "output.log")
    
    os.makedirs(job_dir, exist_ok=True)
    
    # 1. Profile Shadowing (Golden Master)
    # Note: We assume browser_sessions/google_searcher is our master
    master_profile = os.path.abspath("browser_sessions/google_searcher")
    if os.path.exists(master_profile):
        print(f"Shadowing profile for {job_id}...")
        # Use rsync if available for efficiency, else shutil
        try:
            subprocess.run(["rsync", "-a", "--exclude", "Singleton*", master_profile + "/", profile_dir + "/"], check=True)
        except:
            shutil.copytree(master_profile, profile_dir, dirs_exist_ok=True)
    
    registry.update_job(job_id, status=JobStatus.RUNNING.value, display=display, pid=os.getpid())
    
    processes = []
    try:
        # 2. Start Xvfb
        xvfb = await asyncio.create_subprocess_exec(
            "Xvfb", display, "-screen", "0", "1280x1024x24",
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        processes.append(xvfb)
        await asyncio.sleep(2) # Wait for Xvfb to be ready
        
        # 3. Start Fluxbox (Crucial for window management/screenshots)
        env = os.environ.copy()
        env["DISPLAY"] = display
        fluxbox = await asyncio.create_subprocess_exec(
            "fluxbox", env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
        processes.append(fluxbox)
        await asyncio.sleep(1)
        
        # 4. Execute Agent
        # We call the main orchestrator with specific flags
        with open(log_path, "w") as log_file:
            agent_cmd = [
                sys.executable, "main.py",
                "--topic", topic,
                "--job-id", job_id,
                "--profile", profile_dir
            ]
            
            # Use 'timeout' utility for hard limit if available, or handle in asyncio
            agent = await asyncio.create_subprocess_exec(
                *agent_cmd,
                env=env,
                stdout=log_file,
                stderr=subprocess.STDOUT
            )
            
            try:
                # 45 minutes timeout
                await asyncio.wait_for(agent.wait(), timeout=45 * 60)
                
                if agent.returncode == 0:
                    registry.update_job(job_id, status=JobStatus.COMPLETED.value, end_time=datetime.now().isoformat())
                else:
                    registry.update_job(job_id, status=JobStatus.FAILED.value, error_msg=f"Exit code {agent.returncode}")
            except asyncio.TimeoutError:
                print(f"Job {job_id} timed out!")
                agent.kill()
                registry.update_job(job_id, status=JobStatus.FAILED.value, error_msg="Timeout after 45m")

    except Exception as e:
        print(f"Launcher Error for {job_id}: {e}")
        registry.update_job(job_id, status=JobStatus.FAILED.value, error_msg=str(e))
    finally:
        # Cleanup processes
        for p in processes:
            try:
                p.terminate()
                await p.wait()
            except:
                pass
        # Final cleanup of Xvfb lock files if necessary
        lock_file = f"/tmp/.X{display_num}-lock"
        if os.path.exists(lock_file):
            try: os.remove(lock_file)
            except: pass

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: job_launcher.py <job_id> <topic>")
        sys.exit(1)
    
    asyncio.run(run_job(sys.argv[1], sys.argv[2]))
