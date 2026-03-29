import httpx
import asyncio
import os
import subprocess
import time

async def kill_test():
    print("============================================================")
    print("🚀 STARTING CHAOS KILL-TEST (Survival of the Fittest)")
    print("============================================================")
    
    proxy_url = "http://localhost:9002/v1/chat/completions"
    payload = {
        "model": "browser-agent-gemini",
        "messages": [{"role": "user", "content": "Schreib ein langes Gedicht über die Unzerstörbarkeit von Code."}]
    }

    async with httpx.AsyncClient() as client:
        # 1. Start original request
        print("[1/3] Sending original request to Proxy...")
        task = asyncio.create_task(client.post(proxy_url, json=payload, timeout=300))
        
        # 2. Wait for it to be mid-processing
        print("[2/3] Waiting 20s for processing to begin...")
        await asyncio.sleep(20)
        
        # 3. SHOOT THE BROWSER
        print("💥 CHAOS INJECTION: Killing Chromium inside container!")
        # We use docker exec to kill the main chromium process
        subprocess.run(["docker", "exec", "mcp_gemini_1", "pkill", "-f", "chromium"], capture_output=True)
        
        print("🔍 Checking if system recovers and finishes the task...")
        
        try:
            resp = await task
            if resp.status_code == 200:
                print("✅ SUCCESS: Task survived the Browser-Death!")
                print(f"Snippet: {resp.json()['choices'][0]['message']['content'][:200]}...")
            else:
                print(f"❌ FAILURE: Proxy returned {resp.status_code}")
                print(resp.text)
        except Exception as e:
            print(f"❌ CRITICAL ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(kill_test())
