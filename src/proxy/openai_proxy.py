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

async def ask_browser_agent(prompt: str, model: str = "browser-agent-gemini", request_id: str = "N/A") -> str:
    model_lower = model.lower()
    mcp_host = os.getenv("MCP_HOST_1", "gemini-acc-1")
    mcp_port = os.getenv("MCP_PORT_1", "8000")
    
    if "gpt" in model_lower or "openai" in model_lower:
        mcp_host = os.getenv("MCP_HOST_2", "gemini-acc-2")
        mcp_port = os.getenv("MCP_PORT_2", "8000")
    
    url = f"http://{mcp_host}:{mcp_port}/sse"
    log_proxy_event("MCP_CONNECTION_START", request_id=request_id, url=url)

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
                        
                        log_proxy_event("MCP_TOOL_SUCCESS", request_id=request_id)
                        return result.content[0].text
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
    body = await request.json()
    messages = body.get("messages", [])
    model = body.get("model", "browser-agent-gemini")
    request_id = request.state.request_id

    # Combine messages into a single prompt for the browser agent
    prompt = "\n".join([f"{m['role']}: {m['content']}" for m in messages])
    
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
