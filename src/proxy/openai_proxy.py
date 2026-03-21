from fastapi import FastAPI, Request
import uvicorn
import uuid
import time
import asyncio
from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack
import random

app = FastAPI()

# Wir balancen einfach zwischen Container 1 (8001) und Container 2 (8002)
PORTS = [8001, 8002]

async def ask_browser_agent(prompt: str) -> str:
    port = random.choice(PORTS)
    url = f"http://localhost:{port}/sse"
    print(f"Versuche Container auf Port {port} zu erreichen...")
    
    async with AsyncExitStack() as stack:
        # Verbinde mit dem SSE Endpunkt des Docker-Containers
        sse_obj = await stack.enter_async_context(sse_client(url))
        # sse_obj ist ein Tuple (read_stream, write_stream)
        session = await stack.enter_async_context(ClientSession(sse_obj[0], sse_obj[1]))
        
        # Initialisiere die MCP-Verbindung
        await session.initialize()
        
        # Führe das KI-Studio-Tool aus
        result = await session.call_tool("ask_google_ai_studio", {"prompt": prompt})
        
        if result.isError:
            return f"Fehler vom Container auf Port {port}: {result.content}"
        else:
            # result.content ist eine Liste von TextContent-Objekten
            return result.content[0].text

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    try:
        body = await request.json()
    except Exception:
        body = {}

    messages = body.get("messages", [])
    if not messages:
        return {"error": "No messages provided"}

    # Um Kontext für das Browser-Modell nicht zu verlieren, fügen wir alle System-/User-Prompts zusammen
    # Da wir in einem "dummen" Textfeld in AI Studio tippen, ist das der sicherste Weg, nichts von Aiders Prompts zu verlieren.
    full_prompt = "\n\n".join([f"{m.get('role', 'user').upper()}:\n{m.get('content', '')}" for m in messages])

    print(f"--> Sende vollständigen Prompt an Browser Agent (Länge: {len(full_prompt)} Zeichen)")
    
    try:
        browser_response = await ask_browser_agent(full_prompt)
    except Exception as e:
        browser_response = f"Proxy Interner Fehler: {str(e)}"
        
    print(f"<-- Antwort vom Browser Agent empfangen (Länge: {len(browser_response)} Zeichen)")

    return {
        "id": f"chatcmpl-{uuid.uuid4()}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": body.get("model", "browser-agent-gemini"),
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": browser_response
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(full_prompt) // 4, # grobe Schätzung
            "completion_tokens": len(browser_response) // 4,
            "total_tokens": (len(full_prompt) + len(browser_response)) // 4
        }
    }

if __name__ == "__main__":
    # Startet den Server auf Port 9000
    uvicorn.run(app, host="0.0.0.0", port=9000)
