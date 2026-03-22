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

# Wir balancen aktuell nur zu Container 1 (8001), um visuell auf VNC (5901) zu debuggen
PORTS = [8001]

async def ask_browser_agent(prompt: str, model: str = "browser-agent-gemini") -> str:
    port = random.choice(PORTS)
    url = f"http://localhost:{port}/sse"
    print(f"Versuche Container auf Port {port} zu erreichen per Modell {model}...")

    async with AsyncExitStack() as stack:
        # Verbinde mit dem SSE Endpunkt des Docker-Containers
        sse_obj = await stack.enter_async_context(sse_client(url))
        # sse_obj ist ein Tuple (read_stream, write_stream)
        session = await stack.enter_async_context(ClientSession(sse_obj[0], sse_obj[1]))
        
        # Initialisiere die MCP-Verbindung
        await session.initialize()

        tool_name = "ask_gemini"
        tool_args = {
            "session_id": f"aider_{uuid.uuid4().hex[:8]}",
            "prompt": prompt,
            "model_name": "Gemini 3.1 Pro Preview"
        }
        
        if "chatgpt" in model.lower():
            tool_name = "ask_chatgpt"
            tool_args = {
                "session_id": f"aider_{uuid.uuid4().hex[:8]}",
                "prompt": prompt,
                "model_name": "ChatGPT"
            }
        elif "claude" in model.lower():
            tool_name = "ask_claude"
            tool_args = {
                "session_id": f"aider_{uuid.uuid4().hex[:8]}",
                "prompt": prompt,
                "model_name": "Claude"
            }
        elif "deepseek" in model.lower():
            tool_name = "ask_deepseek"
            tool_args = {
                "session_id": f"aider_{uuid.uuid4().hex[:8]}",
                "prompt": prompt,
                "model_name": "DeepSeek"
            }

        # Führe das KI-Studio-Tool aus
        result = await session.call_tool(tool_name, tool_args)
        if result.isError:
            return f"Fehler vom Container auf Port {port}: {result.content}"
        else:
            # result.content ist eine Liste von TextContent-Objekten
            raw_text = result.content[0].text
            # AI Studio "innerText" zerreißt den Markdown Code Block in:
            # code\nPython\ndownload\ncontent_copy\nexpand_less\n# docker_test.py...
            import re
            
            print(f"Proxy raw length received: {len(raw_text)}")
            return raw_text

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
    
    model_name = body.get("model", "browser-agent-gemini")
    print(f"--> Sende vollständigen Prompt an Browser Agent (Länge: {len(full_prompt)} Zeichen, Modell: {model_name})")
    
    try:
        browser_response = await ask_browser_agent(full_prompt, model=model_name)
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
    # Startet den Server auf Port 9002
    uvicorn.run(app, host="0.0.0.0", port=9002)
