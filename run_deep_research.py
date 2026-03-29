import httpx
import asyncio
import json
import os

async def run_research():
    proxy_url = "http://localhost:9002/v1/chat/completions"
    prompt = """Führe eine Deep-Research-Analyse zu den Top 3 Open-Source-Agent-Orchestratoren (PydanticAI, CrewAI, LangGraph) durch. 
    Vergleiche sie hinsichtlich ihrer Eignung für zustandslose (stateless) Infrastrukturen und erstelle eine detaillierte technische Bewertung als Markdown-Bericht. 
    Gehe besonders auf folgende Punkte ein:
    1. Speicher-Management (Handhabung von State)
    2. Skalierbarkeit in Docker/Serverless Umgebungen
    3. Eignung für das Model Context Protocol (MCP)"""
    
    payload = {
        "model": "browser-agent-gemini",
        "messages": [{"role": "user", "content": prompt}]
    }
    
    print("============================================================")
    print("🚀 LAUNCHING DEEP RESEARCH MISSION: AGENT ORCHESTRATORS")
    print("============================================================")
    
    async with httpx.AsyncClient() as client:
        try:
            # We use a very long timeout because this is a complex research task
            resp = await client.post(proxy_url, json=payload, timeout=600)
            if resp.status_code == 200:
                result = resp.json()
                content = result['choices'][0]['message']['content']
                
                # Save the final report
                with open("RESEARCH_REPORT_ORCHESTRATORS.md", "w", encoding="utf-8") as f:
                    f.write(content)
                
                print("✅ MISSION SUCCESS: Research Report saved as RESEARCH_REPORT_ORCHESTRATORS.md")
                print("============================================================")
                print(f"Snippet:\n{content[:500]}...")
            else:
                print(f"❌ MISSION FAILED: Status {resp.status_code}")
                print(resp.text)
        except Exception as e:
            print(f"❌ MISSION ERROR: {e}")

if __name__ == "__main__":
    asyncio.run(run_research())
