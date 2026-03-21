import asyncio
import traceback
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import anyio

async def trigger_agent(agent_name: str, port: int, prompt: str, session_id: str):
    try:
        print(f"[{agent_name}] Verbinde via MCP SSE mit Port {port}...")
        url = f"http://localhost:{port}/sse"
        async with sse_client(url) as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                print(f"[{agent_name}] Sende an Port {port}: '{prompt}'")
                
                result = await session.call_tool(
                    "ask_gemini", 
                    arguments={
                        "session_id": session_id,
                        "prompt": prompt
                    }
                )
                
                print(f"\n[{agent_name} - Port {port}] 🎯 ERKLÄRT FERTIG!")
                for content in result.content:
                    print(f"[{agent_name}] Antwort:\n{content.text}\n")
                    
    except Exception as e:
        print(f"[{agent_name}] ❌ Fehler: {e}")
        traceback.print_exc()

async def main():
    print("=== STARTE ORCHESTRATOR TEST: 2 ACCOUNTS PARALLEL ===")
    # Baldyboy = 8001, BookNuggets = 8002
    await asyncio.gather(
        trigger_agent("Baldyboy (Acc 1)", 8001, "Gib mir EINEN einfaellsreichen Buchtitel ueber kuenstliche Intelligenz (kurz).", "session_A"),
        trigger_agent("BookNuggets (Acc 2)", 8002, "Wie viele Buecher (nicht Filme!) gehoeren zur Lord of the Rings Trilogie? (kurz)", "session_B")
    )
    print("=== TEST BEENDET ===")

if __name__ == "__main__":
    anyio.run(main)
