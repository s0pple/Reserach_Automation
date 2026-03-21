# Decision Record: MCP Browser Architecture & Concurrency

## Challenge
Should we build one monolithic MCP server that controls all LLMs (Gemini, Claude, GPT), or multiple independent MCP servers (one per LLM provider)? 
Furthermore, how do we handle Playwright browser instances without blowing up the system (RAM/CPU) or causing race conditions when multiple agents try to talk to the browser at the same time?

## Decision
We will build **ONE flexible MCP Server** (a central Browser Hub) that can dynamically interact with different LLM interfaces, rather than building strictly separate servers per provider.

### Concurrency Strategy & Limits:
1. **Tool Locks (Mutex):** We will use synchronous task queues or Mutex-Locks. If Subagent A wants to talk to Gemini, and Script B suddenly asks for ChatGPT, the MCP Server will process them **sequentially**. It will not allow parallel mouse clicks.
2. **Context Switching:** We launch one Playwright process. Under the hood, Playwright uses **different browser contexts (Profiles)** depending on which Google/User account is requested. 
3. **RAM Control:** We strict limit the maximum number of concurrent active contexts (e.g., max 3). If a fourth session is requested, the oldest idle tab is put to sleep.
4. **Collision Avoidance:** Because it is deeply centralized in one Server, we have a total overview. We can ensure the mouse/keyboard don't fight each other, avoiding the issue where "Script 1 clicks left while Agent 2 clicks right".
