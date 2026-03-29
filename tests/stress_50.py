import httpx
import asyncio
import time
import json

async def endurance_test(num_req=50):
    print("============================================================")
    print(f"🚀 STARTING ENDURANCE TEST: {num_req} REQUESTS (SEQUENTIAL)")
    print("============================================================")
    
    proxy_url = "http://localhost:9002/v1/chat/completions"
    successes = 0
    failures = 0
    start_time = time.time()

    async with httpx.AsyncClient() as client:
        for i in range(1, num_req + 1):
            print(f"[{i}/{num_req}] Sending Request (ID: endurance-{i})...")
            payload = {
                "model": "browser-agent-gemini",
                "messages": [{"role": "user", "content": f"Task {i}: Schreib einen kurzen Tipp fuer Python-Entwickler ({i})."}]
            }
            
            try:
                resp = await client.post(proxy_url, json=payload, timeout=300)
                if resp.status_code == 200:
                    successes += 1
                    snippet = resp.json()["choices"][0]["message"]["content"][:50].replace("\n", " ")
                    print(f"  ✅ SUCCESS | Length: {len(resp.json()['choices'][0]['message']['content'])} | Snippet: {snippet}...")
                else:
                    failures += 1
                    print(f"  ❌ FAILURE | Status: {resp.status_code} | Details: {resp.text[:100]}")
            except Exception as e:
                failures += 1
                print(f"  ❌ CRITICAL ERROR: {e}")
            
            # Small cooldown during endurance
            await asyncio.sleep(2)

    end_time = time.time()
    duration = end_time - start_time
    print("============================================================")
    print(f"🏁 ENDURANCE TEST FINISHED")
    print(f"Total Requests: {num_req}")
    print(f"Total Success:  {successes}")
    print(f"Total Failures: {failures}")
    print(f"Avg Time per Task: {duration/num_req:.1f}s")
    print(f"Success Rating: {successes/num_req*100:.1f}%")
    print("============================================================")

if __name__ == "__main__":
    asyncio.run(endurance_test(50))
