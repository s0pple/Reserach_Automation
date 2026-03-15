# Plan 07: The General Agent Architecture (Hybrid AI)

**Date:** March 14, 2026
**Status:** Ideation / Conceptual

## The Vision: The Universal "Hunter-Gatherer"
The goal is to evolve the system from a static pipeline (Venture Analyst) into a dynamic, general-purpose agent that can tackle any goal (e.g., "Find the price of cheap bananas at Migros" or "Research a new AI startup").

## Core Execution Loop (The ReAct Framework)

1. **The Planning Phase (Zero-Cost Reasoning)**
   - When a goal is received via Telegram, the agent does *not* immediately click around.
   - It drafts a **Plan**.
   - *Cost-Hack:* Instead of using expensive API tokens for complex reasoning, the agent can autonomously open `google.com` or `aistudio.google.com` (via Playwright/Vision), type the prompt into the free web interface, and extract the generated plan.

2. **Tool & Source Selection**
   - The agent reviews the plan and decides which tools are needed:
     - *Does a pre-built script exist?* (e.g., `qwen_researcher.py`) -> Use it.
     - *Is the target a modern SPA with bot protection (like Qwen)?* -> Use **Vision + xdotool** (Sight & Touch).
     - *Is the target a simple directory or Wikipedia?* -> Use **Headless DOM Scraping** (Fast, cheap, reliable).
   - If the agent lacks information, it halts and asks the user via Telegram for clarification or missing credentials.

3. **Iterative Workflow Generation**
   - If navigating an unknown site (like Migros), the agent uses the CV-Bot iteratively:
     - Scan screen -> Find Search Bar -> Click -> Type -> Scan Screen -> Find Product -> Extract Price.
   - It saves successful navigation paths as reusable JSON workflows or OpenCV templates so the next run is instantaneous.

## Strategic Realization
We must embrace **Hybrid Execution**. There is no "one size fits all". 
- **DOM / Headless Scraping:** Best for simple text extraction.
- **Vision / Xvfb:** Best for bypassing Bot-Walls and complex, JS-heavy web apps.
- **Free Web UIs:** Best for heavy reasoning and planning without API costs.

We will test multiple approaches per use case and dynamically route tasks to the most efficient method.
