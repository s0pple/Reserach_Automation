import httpx
import asyncio
import subprocess
import time
import os
import json

async def task(i, client):
    proxy_url = "http://localhost:9002/v1/chat/completions"
    payload = {
        "model": "browser-agent-gemini",
        "messages": [{"role": "user", "content": f"Task {i}: Generiere eine kurze technische Analyse zu {i*5} Megawatt-Turbinen."}]
    }
    print(f"[Client] Sending Request {i}...")
    try:
        resp = await client.post(proxy_url, json=payload, timeout=400)
        status = "✅ SUCCESS" if resp.status_code == 200 else f"❌ ERROR {resp.status_code}"
        print(f"[Client] Request {i} finished: {status}")
        return i, resp.status_code
    except Exception as e:
        print(f"[Client] Request {i} FAILED: {e}")
        # On timeout, we check the results directory
        return i, 408

async def main():
    print("============================================================")
    print("🏰 IRON FORTRESS: MASSIVE LOAD CERTIFICATION (20 Tasks)")
    print("============================================================")
    
    async with httpx.AsyncClient() as client:
        # 1. Fire 20 parallel requests
        tasks = [asyncio.create_task(task(i, client)) for i in range(1, 21)]
        
        # 2. Wait 40s (enough for many to be active)
        print("⏳ Waiting 40s for mass-processing...")
        await asyncio.sleep(40)
        
        # 3. CHAOS: Kill browser and wait
        print("💥 CHAOS INJECTION: Killing Chromium mid-flight!")
        subprocess.run(["docker", "exec", "mcp_gemini_1", "pkill", "-f", "chromium"], capture_output=True)
        
        # 4. Gather results
        results = await asyncio.gather(*tasks)
        
    print("============================================================")
    print("🏁 CERTIFICATION SUMMARY")
    successes = [r for r in results if r[1] == 200]
    print(f"Total: {len(results)} | Success: {len(successes)} | Success-Rate: {(len(successes)/20)*100}%")
    
    # 5. Check Result Store (Double safety)
    res_dir = "e:/TEST_SYNC/10_projekte_dashboard/10.1_aktiv/Research_Automation/data/results"
    if os.path.exists(res_dir):
        files = os.listdir(res_dir)
        print(f"Final Count in Result-Store: {len(files)}")
    
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
