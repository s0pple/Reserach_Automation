# Knowledge Base: Tech Stack Expansion & Research Insights

This document tracks external repositories and technologies that can enhance our Research Automation architecture (God Container, CV-Bot, Hybrid Router).

## 🥇 Priority 1: Core System Stability & Memory
### 1. [promptfoo](https://github.com/promptfoo/promptfoo) (Testing Framework)
*   **Role:** Quality Gate for LLM outputs.
*   **Integration:** Use it to benchmark our **Local Router** (Ollama) and **Vision Self-Healing** prompts. Ensures that switching models (e.g., Qwen to Llama) doesn't break our JSON-Intent structure.
*   **Next Step:** Integrate into our CI/CD or testing suite to validate tool-call accuracy.

### 2. [volcengine/OpenViking](https://github.com/volcengine/OpenViking) (Context & Memory)
*   **Role:** Hierarchical Long-Term Memory (L0/L1/L2).
*   **Integration:** Serves as the "Hard Drive" for the God Container. Instead of session-only memory, we use this to store CV-Templates, previous research findings, and agent states in a structured, file-system-like way.
*   **Next Step:** Research implementation for a persistent memory layer in `src/core/persistence.py`.

---

## 🥈 Priority 2: Agent Intelligence & Specialized Analysis
### 3. [agency-agents](https://github.com/msitarzewski/agency-agents) (Agent Personas)
*   **Role:** Library of 140+ specialized AI identities.
*   **Integration:** Enhances our **Router** ("Senior Dispatcher") and **Venture Analyst** (e.g., "Market Expert", "Reality Checker"). We can inject these personas into our system prompts to increase output quality.
*   **Next Step:** Map specific personas to our existing `ToolRegistry` agents.

### 4. [666ghj/MiroFish](https://github.com/666ghj/MiroFish) (Swarm & CV Logic)
*   **Role:** Multi-agent simulation and low-latency CV interaction.
*   **Integration:**
    *   **CV:** Use as reference for millisecond-fast visual triggers in the CV-Bot.
    *   **Swarm:** Use later for "Expert Panels" to evaluate venture memos from multiple perspectives.
*   **Next Step:** Analyze the CV-detection loop for integration into `workflow_manager.py`.

---

## 🥉 Priority 3: Specialized & Future-Proofing
### 5. [p-e-w/heretic](https://github.com/p-e-w/heretic) (Abliteration / Uncensored Reasoning)
*   **Role:** Removing moral/safety filters from local models.
*   **Integration:** Relevant if our research hits "sensitive" boundaries (e.g., analyzing controversial markets or stress-testing systems) where standard models might refuse to process data.
*   **Next Step:** Keep as a fallback for the Local Router if we encounter refusal issues.

### 6. [pbakaus/impeccable](https://github.com/pbakaus/impeccable) (UI/UX for AI)
*   **Role:** Design rules for AI-generated interfaces.
*   **Integration:** Lower priority for our current backend focus, but useful if the Telegram Bot ever evolves into a full Web UI or if we need to generate "beautiful" research reports.

### 7. [karpathy/nanochat](https://github.com/karpathy/nanochat) (Minimalist UI/Architecture)
*   **Role:** High-performance, low-bloat chat logic.
*   **Integration:** Architectural reference for our Local Router interface. Keeps the system "Zero-Cost" and fast.
