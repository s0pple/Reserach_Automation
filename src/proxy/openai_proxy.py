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

@app.middleware("http")
async def log_requests(request: Request, call_next):
    print(f"DEBUG: Incoming {request.method} to {request.url.path}")
    response = await call_next(request)
    print(f"DEBUG: Response status: {response.status_code}")
    return response

# Wir balancen aktuell nur zu Container 1 (8001), um visuell auf VNC (5901) zu debuggen
PORTS = [8001]

async def ask_browser_agent(prompt: str, model: str = "browser-agent-gemini") -> str:
    model_lower = model.lower()
    if "aistudio" in model_lower or "gemini" in model_lower:
        port = 8001
    else:
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

        model_lower = model.lower()
        if "aistudio" in model_lower or "gemini" in model_lower:
            tool_name = "ask_gemini"
            target_port = 8001
            tool_args = {
                "session_id": f"aider_{uuid.uuid4().hex[:8]}",
                "prompt": prompt,
                "model_name": "Gemini 3.1 Pro Preview"
            }
        elif "chatgpt" in model_lower:
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
        elif "perplexity" in model.lower():
            tool_name = "ask_perplexity"
            tool_args = {
                "session_id": f"aider_{uuid.uuid4().hex[:8]}",
                "prompt": prompt,
                "model_name": "Perplexity"
            }
        else:
            # Fallback for generic names like gpt-4o
            print(f"DEBUG: Unknown model mapping for '{model}', falling back to Gemini")
            tool_name = "ask_gemini"
            tool_args = {
                "session_id": f"aider_{uuid.uuid4().hex[:8]}",
                "prompt": prompt,
                "model_name": "Gemini 3.1 Pro Preview"
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

@app.get("/v1/models")
@app.get("v1/models")  # Ohne Slash
@app.get("/models")
@app.api_route("/{path:path}", methods=["GET"])
async def models_fallback(path: str = None):
    if path and "models" in path:
        return {"object": "list", "data": [{"id": "browser-agent-aistudio", "object": "model"}]}
    return {"error": "not found"}

@app.post("/{path:path}")
async def final_catch_all(request: Request, path: str):
    original_body = {}
    try:
        original_body = await request.json()
    except Exception as e:
        print(f"DEBUG: Fehler beim Parsen des Request-Body: {e}")

    if "input" in original_body and "messages" not in original_body:
        original_body["messages"] = original_body.pop("input")
        print("DEBUG: Payload gemappt (input -> messages)")

    print(f"🚀 Starte Browser-Logik für Pfad: {path}")
    return await chat_completions(request, override_body=original_body)

async def chat_completions(request: Request, override_body: dict = None):
    body = override_body if override_body is not None else {}
    if not body:
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
        import traceback
        traceback.print_exc()
        browser_response = f"Proxy Interner Fehler: {str(e)}"
        
    print(f"<-- Antwort vom Browser Agent empfangen (Länge: {len(browser_response)} Zeichen)")

    # 1. Radikaler Response-Strip: Entferne alles, was identisch zum Prompt ist (falls Echo auftritt)
    cleaned_response = browser_response
    if browser_response.startswith(full_prompt):
        cleaned_response = browser_response[len(full_prompt):].strip()
        print(f"✂️ Echo entfernt. Neue Länge: {len(cleaned_response)} Zeichen")
    
    # 2. Debug-Print für OpenClaw
    print(f"!!! SENDING TO OPENCLAW: {cleaned_response[:500]}...")

    # 3. Exakter OpenAI JSON Standard
    final_json = {
        "id": f"chatcmpl-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": "browser-agent-aistudio",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": cleaned_response
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": max(1, len(full_prompt) // 4),
            "completion_tokens": max(1, len(cleaned_response) // 4),
            "total_tokens": max(1, (len(full_prompt) + len(cleaned_response)) // 4)
        }
    }
    print(f"!!! SENDING TO OPENCLAW: {str(cleaned_response)[:150]}...")
    return final_json

if __name__ == "__main__":
    # Startet den Server auf Port 9002
    uvicorn.run(app, host="0.0.0.0", port=9002)
