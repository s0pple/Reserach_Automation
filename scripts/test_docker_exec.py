import subprocess
import sys
import time

def run_command(cmd, name):
    print(f"\n--- Running: {name} ---")
    print(f"Command: {' '.join(cmd)}")
    try:
        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            encoding='utf-8',
            errors='replace'
        )
        
        # Stream output
        for line in process.stdout:
            print(f"  [Output] {line.strip()}")
            
        process.wait()
        if process.returncode == 0:
            print(f"✅ {name} SUCCESS")
            return True
        else:
            print(f"❌ {name} FAILED (Exit Code: {process.returncode})")
            return False
    except Exception as e:
        print(f"💥 {name} CRASHED: {e}")
        return False

def main():
    container = "mcp_gemini_1"
    openclaw_path = "/app/openclaw-main"
    
    print(f"🚀 [Verification] Starting Bridge Test for {container}...")

    # 1. Basic Connectivity & Node Version
    if not run_command(["docker", "exec", container, "node", "-v"], "Node Version Check"):
        print("🛑 Critical Failure: Node not found in container. Did you rebuild?")
        return

    # 2. PNPM Installation Check
    if not run_command(["docker", "exec", container, "pnpm", "-v"], "pnpm Version Check"):
        print("🛑 Critical Failure: pnpm not found in container.")
        return

    # 3. PNPM Install (Initialize isolated node_modules)
    print("\n📦 [Info] Running pnpm install inside container (Isolating Linux binaries)...")
    print("   This might take 1-2 minutes on the first run.")
    if not run_command(["docker", "exec", "-w", openclaw_path, container, "pnpm", "install"], "Container-Side pnpm Install"):
        print("⚠️ pnpm install failed, but continuing to see if existing modules work...")

    # 4. OpenClaw Help Test
    if not run_command(["docker", "exec", container, "node", f"{openclaw_path}/openclaw.mjs", "--help"], "OpenClaw Help Test"):
        print("🛑 Critical Failure: OpenClaw execution failed.")
        return

    # 5. LIVE BROWSER TEST (The Moment of Truth)
    print("\n🎬 [Action] Triggering LIVE Browser Test...")
    print("👉 WATCH YOUR VNC WINDOW (Port 5901) NOW!")
    
    # We use a simple google search to prove rendering
    browser_cmd = [
        "docker", "exec", 
        "-e", "DISPLAY=:99",
        container, 
        "node", f"{openclaw_path}/openclaw.mjs", 
        "agent", "--local", "--agent", "main", 
        "-m", "open google.com and wait 5 seconds"
    ]
    
    if run_command(browser_cmd, "Live Browser Execution"):
        print("\n🏆 MISSION ACCOMPLISHED: The bridge is stable and rendering in VNC.")
    else:
        print("\n💀 Browser test failed. Check VNC for error messages.")

if __name__ == "__main__":
    main()
