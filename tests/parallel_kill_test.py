import httpx
import asyncio
import subprocess
import time

async def task(i, client):
    proxy_url = "http://localhost:9002/v1/chat/completions"
    payload = {
        "model": "browser-agent-gemini",
        "messages": [{"role": "user", "content": f"Task {i}: Schreib einen kurzen Bericht ueber {i*10} Jahre KI-Forschung."}]
    }
    print(f"[Client] Sending Request {i}...")
    try:
        resp = await client.post(proxy_url, json=payload, timeout=360)
        status = "✅ SUCCESS" if resp.status_code == 200 else f"❌ ERROR {resp.status_code}"
        content = resp.text[:100].replace("\n", " ")
        print(f"[Client] Request {i} finished: {status} | Snippet: {content}...")
        return i, resp.status_code
    except Exception as e:
        print(f"[Client] Request {i} FAILED: {e}")
        return i, 500

async def main():
    print("============================================================")
    print("🏰 FORTRESS VALIDATION: PARALLEL KILL-TEST")
    print("============================================================")
    
    async with httpx.AsyncClient() as client:
        # 1. Fire 5 parallel requests
        tasks = [asyncio.create_task(task(i, client)) for i in range(1, 6)]
        
        # 2. Wait 25s for processing
        print("⏳ Waiting 25s for tasks to reach the Browser...")
        await asyncio.sleep(25)
        
        # 3. SHOOT THE BROWSER
        print("💥 CHAOS INJECTION: Killing Chromium mid-flight!")
        subprocess.run(["docker", "exec", "mcp_gemini_1", "pkill", "-f", "chromium"], capture_output=True)
        
        # 4. Gather results
        print("🔍 Monitoring recovery and terminal states...")
        results = await asyncio.gather(*tasks)
        
    print("============================================================")
    print("🏁 TEST SUMMARY")
    successes = [r for r in results if r[1] == 200]
    failures = [r for r in results if r[1] != 200]
    print(f"Total: {len(results)} | Success: {len(successes)} | Fail: {len(failures)}")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(main())
