from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse
import uvicorn
import uuid
import time
import asyncio
import sys
import os
import codecs

# Force UTF-8 for console output on Windows to prevent UnicodeEncodeError
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

from mcp.client.session import ClientSession
from mcp.client.sse import sse_client
from contextlib import AsyncExitStack
import random

app = FastAPI()

def log_proxy_event(event_name: str, request_id: str = "N/A", **kwargs):
    import json
    payload = {
        "event": event_name,
        "request_id": request_id,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        **kwargs
    }
    print(f"[EVENT] {json.dumps(payload)}")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    request.state.request_id = str(uuid.uuid4())
    log_proxy_event("HTTP_REQUEST_RECEIVED", request_id=request.state.request_id, method=request.method, path=request.url.path)
    response = await call_next(request)
    log_proxy_event("HTTP_RESPONSE_SENT", request_id=request.state.request_id, status=response.status_code)
    return response

# Global Round-Robin Counter
mcp_index = 0

async def ask_browser_agent(prompt: str, model: str = "browser-agent-gemini", request_id: str = "N/A") -> str:
    global mcp_index
    model_lower = model.lower()
    
    # Discovery: Find all MCP hosts from environment
    mcp_hosts = []
    i = 1
    while True:
        host = os.getenv(f"MCP_HOST_{i}")
        if not host: break
        port = os.getenv(f"MCP_PORT_{i}", "8000")
        mcp_hosts.append((host, port))
        i += 1
    
    if not mcp_hosts:
        # ARE Hardening: Locked Single-Host for Validation
        mcp_hosts = [("gemini-acc-1", "8000")]
        MCP_SERVERS = [f"http://{mcp_hosts[0][0]}:8000/sse"]

    # Select host (Round Robin)
    host, port = mcp_hosts[mcp_index % len(mcp_hosts)]
    mcp_index += 1
    
    url = f"http://{host}:{port}/sse"
    log_proxy_event("MCP_CONNECTION_START", request_id=request_id, url=url, worker_pool_size=len(mcp_hosts))

    try:
        async with AsyncExitStack() as stack:
            # ARE: Handshake headers. Host header is now allowed thanks to server-side monkeypatch.
            headers = {
                "Accept": "text/event-stream"
            }
            async with sse_client(url, headers=headers) as streams:
                client_input, client_output = streams
                async with ClientSession(client_input, client_output) as session:
                    await session.initialize()
                    
                    # Tool Routing Logic
                    if "SAVE_FILE:" in prompt.split("\n")[0]:
                        # Extract filename from first line, content from rest
                        first_line = prompt.split("\n")[0]
                        header = first_line.split("SAVE_FILE:")[1].strip()
                        content = prompt.split("\n", 1)[1] if "\n" in prompt else ""
                        tool_name = "write_research_file"
                        tool_args = {"filename": header, "content": content}
                    else:
                        tool_name = "ask_gemini" if "gemini" in model_lower or "aistudio" in model_lower else "ask_chatgpt"
                        tool_args = {
                            "session_id": f"session_{request_id[:8]}",
                            "prompt": prompt,
                            "model_name": "Gemini 1.5 Pro" if "1.5" in model_lower else "Gemini 1.0 Pro"
                        }
                    
                    log_proxy_event("MCP_TOOL_CALL", request_id=request_id, tool=tool_name)
                    
                    # ARE Hardening: Increased timeout for Plan D cycles
                    async with asyncio.timeout(300.0):
                        result = await session.call_tool(tool_name, tool_args)
                        
                        result_text = result.content[0].text if result.content else "EMPTY_CONTENT"
                        log_proxy_event("MCP_TOOL_SUCCESS", request_id=request_id, snippet=result_text[:200])
                        return result_text
    except asyncio.TimeoutError:
        log_proxy_event("MCP_TIMEOUT", request_id=request_id, timeout=300)
        return "Error: MCP tool call timed out after 300s (Plan D loop took too long or failed)."
    except Exception as e:
        import traceback
        current_time = time.ctime()
        with open("/app/proxy_error.log", "a") as f:
            f.write(f"\n--- ERROR at {current_time} (Request: {request_id}) ---\n")
            f.write(traceback.format_exc())
            f.write("\n")
        
        log_proxy_event("MCP_ERROR", request_id=request_id, error=str(e))
        return f"Error: {str(e)}"

@app.post("/v1/responses")
async def legacy_responses(request: Request):
    return await chat_completions(request)

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):
    # Deep Sniffer: Log and check raw body for universal [local] detection
    raw_body = await request.body()
    raw_str = raw_body.decode('utf-8', errors='replace').lower()
    
    body = await request.json()
    model = body.get("model", "browser-agent-gemini")
    request_id = request.state.request_id

    # Combine messages, input, or prompt into a single prompt string
    messages = body.get("messages", [])
    input_field = body.get("input", [])
    prompt_field = body.get("prompt", "")
    
    if messages:
        prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    elif input_field:
        # OpenClaw specific hybrid format
        if isinstance(input_field, list):
            prompt = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in input_field])
        else:
            prompt = str(input_field)
    elif prompt_field:
        prompt = prompt_field if isinstance(prompt_field, str) else str(prompt_field)
    else:
        prompt = ""

    model = body.get("model", "browser-agent-gemini")
    request_id = request.state.request_id
    model_lower = model.lower()
    
    # ARE Phase 3 Refined: Explicit Local Routing
    # Surgical check: Trigger ONLY if [local] is in a USER message.
    # We handle both string and structured list content formats.
    def get_text(content):
        if isinstance(content, str):
            return content
        if isinstance(content, list):
            return "\n".join([item.get("text", "") for item in content if isinstance(item, dict) and "text" in item])
        return str(content)

    use_local_ai = False
    last_user_content = ""
    for msg in reversed(messages):
        if msg.get("role") == "user":
            content = msg.get("content", "")
            if isinstance(content, list):
                last_user_content = " ".join([c.get("text", "") for c in content if c.get("type") == "text"])
            else:
                last_user_content = str(content)
            break
            
    if "[force_local_ollama]" in last_user_content:
        use_local_ai = True
        log_proxy_event("PROXY_ROUTING_DECISION", request_id=request_id, use_local_ai=True, model=model, user_snippet=last_user_content[:100])
    else:
        log_proxy_event("PROXY_ROUTING_DECISION", request_id=request_id, use_local_ai=False, model=model, user_snippet=last_user_content[:100])
    
    if use_local_ai:
        import httpx
        log_proxy_event("OLLAMA_ROUTING_START", request_id=request_id, model="llama3.1")
        try:
            # We use the OpenAI-compatible endpoint of Ollama
            ollama_url = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434/v1/chat/completions")
            async with httpx.AsyncClient(timeout=120.0) as client:
                ollama_response = await client.post(
                    ollama_url,
                    json={
                        "model": "llama3.1",
                        "messages": [
                            {"role": "system", "content": "You are a precise tool-calling assistant. Respond ONLY with the requested tool call or text. Keep it brief. Do not use prosy chatter."},
                            {"role": "user", "content": prompt.replace("[LOCAL]", "").strip()}
                        ],
                        "temperature": 0.1
                    }
                )
                ollama_data = ollama_response.json()
                response_text = ollama_data["choices"][0]["message"]["content"]
                log_proxy_event("OLLAMA_SUCCESS", request_id=request_id, snippet=response_text[:200])
                return {
                    "id": f"chatcmpl-{request_id}",
                    "object": "chat.completion",
                    "created": int(time.time()),
                    "model": model,
                    "choices": [
                        {
                            "index": 0,
                            "message": {
                                "role": "assistant",
                                "content": response_text
                            },
                            "finish_reason": "stop"
                        }
                    ],
                    "usage": {
                        "prompt_tokens": len(prompt.split()),
                        "completion_tokens": len(response_text.split()),
                        "total_tokens": len(prompt.split()) + len(response_text.split())
                    }
                }
        except Exception as e:
            log_proxy_event("OLLAMA_ERROR", request_id=request_id, error=str(e))
            return f"Error: Ollama fallback failed: {str(e)}"

    # Standard Path: Research via MCP / AI Studio
    response_text = await ask_browser_agent(prompt, model=model, request_id=request_id)
    
    return {
        "id": f"chatcmpl-{request_id}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": response_text
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {
            "prompt_tokens": len(prompt.split()),
            "completion_tokens": len(response_text.split()),
            "total_tokens": len(prompt.split()) + len(response_text.split())
        }
    }

@app.get("/health")
async def health():
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=5000)
