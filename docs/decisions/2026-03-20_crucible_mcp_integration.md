# Architecture Decision: The Crucible as an MCP Microservice

**Date:** 2026-03-20
**Status:** Approved / In Progress

## Context
The goal is to integrate "free cloud LLM" logic (specifically automating Google AI Studio via browser) into OpenClaw without polluting the core TypeScript codebase with Python/Playwright dependencies and without blocking the main event loop ("Asynchronous Hell").

## Decision
We will implement "The Crucible" (the Python/Playwright automation engine) as a **standalone MCP (Model Context Protocol) Server**.

### Architecture
1.  **OpenClaw (Node.js)**: Acts as the MCP Client. It sees a tool called `ask_google_ai_studio`.
2.  **The Crucible (Python Docker Container)**: Runs the MCP Server.
    *   **Stack**: Python 3.11, Playwright, Xvfb (for headless display).
    *   **Transport**: Stdio (Docker exec) or SSE (Server-Sent Events).
3.  **Communication**:
    *   OpenClaw sends a JSON-RPC request: `{ "method": "tools/call", "params": { "name": "ask_google_ai_studio", "arguments": { "prompt": "..." } } }`.
    *   The Crucible receives this, spins up the browser (if not running), performs the automation, and returns the result string.

## Technical Findings (Prototyping)
We prototyped the core automation logic in `test_ai_studio_streaming.py`.

### 1. Robust Streaming Detection
The biggest challenge is detecting when the LLM has finished generating text without using fixed sleeps.
*   **Start Detection**: The "Run" button (`button[aria-label='Run']`) **disappears** (or becomes hidden) immediately when generation starts. This is a reliable trigger.
*   **End Detection**: The "Run" button reappears, OR a "Stop" button disappears. Our prototype successfully detected the start but timed out waiting for the Run button to return, suggesting we might need to look for the "Stop" button's disappearance or handle a "Follow-up" button state.

### 2. Validated Selectors
*   **Input**: `textarea[aria-label='Enter a prompt']`
*   **Run Button**: `button[aria-label='Run']`
*   **Response**: `ms-text-chunk` (Standard) or `.model-turn` (Fallback).

## Implementation Plan
1.  **Finalize `crucible_mcp_server.py`**: Wrap the proven logic from `test_ai_studio_streaming.py` into a FastMCP class.
2.  **Dockerize**: Create `Dockerfile.crucible` including Playwright, Xvfb, and the MCP server.
3.  **Connect**: Configure OpenClaw's `config.json` (or equivalent) to spawn this Docker container as an MCP server.

## Benefits
*   **Decoupling**: OpenClaw doesn't need to know about Playwright or Python.
*   **Stability**: If the browser crashes, it doesn't take down the main agent.
*   **Reusability**: This "Free LLM" tool can be used by *any* MCP-compliant agent (Cursor, Claude Desktop, etc.), not just OpenClaw.
