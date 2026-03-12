# Architecture Decision Record (ADR): Build vs. Buy (Custom Orchestrator vs. Generalist Agents like OpenClaw)
**Date:** March 11, 2026

## Context
The question arose whether it is worthwhile to build and maintain a custom "Motherboard" (`orchestrator.py` + `registry.py`) instead of using large, open-source generalist frameworks like OpenClaw or AutoGPT, which also offer LLM routing and UI automation.

## Analysis: Generalist vs. The Assembly Line

### The Generalist Approach (e.g., OpenClaw)
- **Mechanism:** "Sense-Think-Act". Takes a screenshot -> sends to Vision LLM -> LLM calculates X/Y -> executes mouse click.
- **Strengths:** Can handle completely unknown websites and zero-shot tasks (e.g., "Book a flight on a site I've never seen"). Highly resilient to UI changes if the Vision model is strong enough.
- **Weaknesses:**
  - **Cost:** Extremely expensive. Requires state-of-the-art Vision models (Claude 3.5 Sonnet / GPT-4o). Local vision models are either too weak or require massive hardware.
  - **Speed:** Very slow (5-15 seconds per click loop).
  - **Data Extraction:** Terrible at extracting massive amounts of structured text (e.g., pulling a 20k word Markdown report). It sees pixels, not the DOM/Clipboard.

### Our Custom System (The Assembly Line)
- **Mechanism:** Specialized, hardcoded logic blocks connected by a fast Semantic Router.
  - **Vision:** OpenCV/PyAutoGUI for instantaneous pixel-template matching (0.1s response).
  - **Extraction:** Playwright directly interrogates the DOM or Clipboard.
  - **Reasoning:** A highly specialized VC-Agent pipeline ("The Crucible") designed exclusively for analyzing market gaps.
- **Strengths:**
  - **Zero-Cost Scaling:** Bypasses API costs entirely by utilizing local models (Ollama `qwen3:8b`) for routing and automating the free web UI of Gemini for heavy research.
  - **Speed:** Immediate execution for known templates.
  - **Domain Expertise:** Built specifically for Venture Capital logic, not generic tasks.

## Decision
**We will continue building our custom Orchestrator.**
The project is not about reinventing the wheel (we still use Open-Source libs like Playwright and Ollama), but rather about gluing them together with specific Business Logic to bypass API costs and maintain extreme speed.

### Future Extensibility
Because our architecture is built around a modular `ToolRegistry`, if we ever need a generalist agent to navigate the "unknown web", we can simply wrap a tool like OpenClaw inside our system. The Local Router will then say: *"This task requires navigating an unknown UI -> Delegate to the OpenClaw Tool."*

This preserves absolute control while keeping the core fast and free.
