import asyncio
from mcp.client.sse import sse_client
from mcp.client.session import ClientSession
import anyio

async def trigger_agent(agent_name: str, prompt: str, session_id: str):
    try:
        print(f"[{agent_name}] Verbinde via MCP SSE mit dem God-Container...")
        async with sse_client("http://localhost:8000/sse") as streams:
            async with ClientSession(streams[0], streams[1]) as session:
                await session.initialize()
                
                print(f"[{agent_name}] Sende Tool Call: ask_gemini -> '{prompt}'")
                
                result = await session.call_tool(
                    "ask_gemini", 
                    arguments={
                        "session_id": session_id,
                        "prompt": prompt
                    }
                )
                
                # result.content ist eine Liste von TextContent objekten
                print(f"\n[{agent_name}] 🎯 ERKLÄRT FERTIG!")
                for content in result.content:
                    print(f"[{agent_name}] Antwort:\n{content.text}\n")
                    
    except Exception as e:
        import traceback
        print(f"[{agent_name}] ❌ Fehler: {e}")
        traceback.print_exc()

async def main():
    print("=== STARTE LAST-TEST: 2 AGENTEN GLEICHZEITIG ===")
    await asyncio.gather(
        trigger_agent("Agent Alpha", "Was ist die Hauptstadt von Frankreich? Antworte mit exakt einem Wort.", "alpha_session"),
        trigger_agent("Agent Beta", "Wie hoch ist der Eiffelturm ca.? Antworte extrem kurz.", "beta_session")
    )
    print("=== TEST BEENDET ===")

if __name__ == "__main__":
    anyio.run(main)
