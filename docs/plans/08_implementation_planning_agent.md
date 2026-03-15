# Plan 08: Implementation of the "Planning Agent" (The Universal Hunter-Gatherer) - REVISED

**Date:** March 14, 2026
**Branch:** `feat/planning-agent`
**Objective:** Evolve the system from a static Qwen-Research pipeline into a dynamic, intent-driven ReAct agent capable of intelligent planning and hybrid execution.

---

## 🧠 Architectural Guidelines & Compliance
1. **API for Logic, Web-UIs for Heavy Lifting:** The core "Brain" (The Planner) MUST use the official Gemini/OpenAI API with strict JSON-Mode for 100% stability. The "Zero-Cost" Web-UI-Hack is strictly reserved for the Execution phase (e.g., massive data extraction), NOT for the control loop itself.
2. **Minimal Invasive Surgery:** The core Telegram Bot (`src/interfaces/telegram/bot.py`) and the Local Router (`src/agents/local_router/router.py`) will be extended, not rewritten.
3. **Reason, Act, OBSERVE (Dynamic Loop):** The planner does not write a rigid 10-step plan. It plans the *next* logical step based on the current `OBSERVATION` (Screenshot/DOM). If a DOM action fails, the Executor falls back to Vision automatically.
4. **State Isolation:** The Planning Agent must run in an isolated environment (`temp/jobs/<job_id>`) to prevent file-lock issues during concurrent execution.

---

## 🛠️ Phased Implementation Plan

### Phase 1: Intent Routing Expansion (The Switch)
**Goal:** The Telegram bot must distinguish between a static research request and a dynamic goal.
- **Action:** Modify `src/agents/local_router/router.py`. 
- **Details:** Add a new intent category: `general_agent_task`.
- **Test:** If the user asks "Was kosten Bananen bei Migros?", the router must return `{"tool": "general_agent", "parameters": {"goal": "Finde Bananenpreise bei Migros"}}`.

### Phase 2: The Planner Module (The Brain)
**Goal:** Build the agent that determines the next best action based on the current state.
- **Location:** `src/agents/general_agent/planner.py`
- **Action:** Create a ReAct-style planning function using the **official Gemini API** (using the Free Tier).
- **Logic:**
  1. Call the API with `response_format="json_object"`.
  2. Input: The user `goal` AND the `current_state` (e.g., current URL, last action result, simplified DOM/Vision context).
  3. Output: A strictly typed JSON object containing the `next_action` (e.g., 'GOTO_URL', 'SEARCH', 'CLICK', 'EXTRACT'), the `target`, and the `expected_result`.

### Phase 3: The Execution Engine (Reason-Act-Observe Loop)
**Goal:** A dynamic loop that acts, observes, and requests the next step.
- **Location:** `src/agents/general_agent/executor.py`
- **Logic:**
  1. Request `next_action` from Planner.
  2. **Act:** The Executor tries the fastest method first (Playwright DOM). If it hits a Bot-Wall or the element is hidden, it autonomously falls back to `CVBotTool` (Vision/xdotool).
  3. **Observe:** Capture the new DOM/Screenshot. Check if `expected_result` was met.
  4. If success -> repeat loop until goal is reached.
  5. If fail -> trigger Fallback/Recovery (send error to Planner for alternative route, max 3 retries).

### Phase 4: Telegram Feedback Loop (Human-in-the-Loop)
**Goal:** Keep the user informed without spamming.
- **Action:** Integrate the Executor into `src/interfaces/telegram/bot.py`.
- **Details:** Use a single, continuously updating Telegram message via `context.bot.edit_message_text` to show the current status (e.g., *"🔄 Status: Suche Suchfeld..."*). The user can use the `/live` stream for visual control. If the 3-retry limit is hit, halt and wait for user chat input.

---

## 🚦 Next Immediate Steps for the AI Developer
1. Verify the local router prompt in `router.py` and add the `general_agent` tool definition.
2. Build the basic skeleton of `src/agents/general_agent/planner.py` using strict JSON schema.
3. Build the Executor Loop skeleton.
