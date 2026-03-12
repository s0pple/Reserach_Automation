# Research Automation System (Venture Analyst Edition)

A modular, evidence-based research engine that transforms unstructured web data into structured venture opportunities. Unlike generic AI researchers, this system uses a "Venture Capital" logic: **Filtering through friction, not just gathering information.**

---

## 🧠 AI Agent Memory & Context (For Future CLI Sessions)

**ATTENTION AI AGENTS:** If you are a new instance of Gemini CLI or any other coding assistant, your **first step** before modifying this codebase is to read the project's historical context and architectural rules.
1. Check the `PROJECT_BOARD.md` to see current tasks and open ideas.
2. Read the Architecture Decision Records (ADRs) in the `docs/decisions/` folder.
   - **Crucial:** Always read the files in `docs/decisions/` sorted by date. The **newest** files contain the most up-to-date rules (e.g., the Phalanx Workflow, Read-Only Infrastructure rules, and Cloud Deployment plans). 

---

## 🚀 Status & Roadmap (Venture Analyst Machine)

| Feature | Status | Rational (Why?) | Next Steps |
| :--- | :--- | :--- | :--- |
| **Venture State Schema** | ✅ Ready | Atomic data structure (`EvidenceClaim`) to prevent "text soup". | Add support for "Negative Evidence". |
| **Evidence Extractor** | ✅ Ready | Surgical filtering of raw text into structured facts (Actor, Context, Pain). | Field-tested with Actor Inference & Noise Rejection. |
| **Problem Graph Builder** | ✅ Ready | The "Refinery": Clusters claims into "Opportunity Nodes" with Venture Scoring. | Implemented Task Normalization & Signal Aggregation. |
| **Competition Mapper** | ✅ Ready | The "Market Scanner": Maps competitors, weaknesses, and identifies the "Gap". | Enriches nodes with competitor features and UX weaknesses. |
| **The Historian** | ✅ Ready | The "Trauma Analyst": Analyzes why previous startups failed to avoid repeating history. | Identifies dead startups, failure patterns, and structural constraints. |
| **Market Timing Agent** | ✅ Ready | The "Trend Analyst": Identifies 'Enablers' (Tech Shifts, Regulation, Cost Collapse). | Analyzes if 'now' is the right time to solve a historical pain. |
| **Differentiation Agent** | ✅ Ready | The "Strategy Engine": Designs winning 10x strategies based on gaps, history, and timing. | Applied patterns like 'API-first', 'Automation-only', and 'Vertical AI'. |
| **The Skeptic (Critic)** | 📅 Planned | Stress-tests strategies by finding distribution risks and saturation. | Implement "Crucible" debate logic per strategy. |
| **VC-Style Reporting** | 📅 Planned | Actionable investment memos instead of long text reports. | Create Markdown templates for Venture Memos. |
| **Browser Integration** | ✅ Ready | Playwright engine to pull real data from Reddit, News, and Forums. | Enhance error resilience for complex site layouts. |
| **Global Research Database** | ✅ Ready | SQLite storage to persist all Venture Runs and Memos. | Add advanced querying/analytics via GUI. |

---

## 🧠 The Architecture: "The Investment Committee"

The system operates like a digital venture firm, following a 4-phase funnel:

1. **Discovery (Explorer/Historian)**: Broad search for trends, pains, and past failures.
2. **Extraction (Evidence Extractor)**: Converting raw text into structured **EvidenceClaims**.
3. **Clustering (Graph Builder)**: Mapping claims into **Opportunity Nodes** and **Idea Clusters**.
4. **Scrutiny (Believer vs. Skeptic)**: Pitting agent personalities against each other to find the "Moat" and "Gaps".

---

## 🛠 Quick Start – Running the Analyst

### 1. Environment Setup
```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
playwright install chromium
```

### 2. Persistent Login (One-Time)
To use Gemini AI Studio or Perplexity without logging in every time:
1. Open `src/modules/browser/provider.py`.
2. Set `headless=False` in the `BrowserSearchProvider` constructor.
3. Run the system once (Step 3). When the browser opens, **manually log in** to your Google/Perplexity account.
4. Close the browser. Your session is now saved in the `browser_session/` folder.
5. Revert to `headless=True` for hands-free operation.

### 3. Run Your First Research
Execute the main entry point. Use `--browser=True` to trigger the Deep Research loop:
```powershell
python run_research.py "analyze AI logistics automation in Europe" --iterations=2 --browser=True
```

### 4. What the Output Looks Like
1. **[POWER MODE]**: System opens a browser, triggers Gemini Deep Research, and scrapes the report.
2. **[IMPORTER]**: The report is parsed into **ResearchNodes** (Hypotheses, Evidence, Sources).
3. **[REFINEMENT]**: The Agent Pipeline (Planner, Collector, Analyst, Critic) runs for X iterations to challenge findings and fill gaps.
4. **[FINAL REPORT]**: A structured Markdown report is printed to the console.

### 5. Immediate Test (No Browser)
If you want to test the logic without opening a browser yet, the system defaults to a **Simulated Browser** if Playwright is missing or if you modify `run_research.py` as shown in the next section.

---

## Architecture
- **Orchestrator**: Manages the iterative loops.
- **ResearchState**: The "Source of Truth" knowledge graph.
- **Agents**: Specialized LLM-powered units (Planner, Analyst, Critic, etc.).
- **Browser Intake**: Converts unstructured AI reports into structured graph data.

---

## 📜 System State & Recent Updates (Developer Log)

**Last Update:** March 2026

To help any future developer (or AI assistant) immediately grasp the current working state and testing setup of the system, here are the latest architectural breakthroughs:

### 1. The Bridge: Pipeline meets Deep Research
The true power of the system has been unlocked by connecting the **Agent Pipeline** (The Crucible) with the **Playwright GUI Automation** (`BrowserSearchProvider`). 
- **Workflow:** The 7 agents synthesize raw data into a structured Venture Memo and generate an `ULTIMATE DEEP RESEARCH PROMPT`. This prompt is stored in the `OpportunityNode` metadata.
- **Phase 4 (The Final Ordeal):** `run_venture_analyst.py` automatically takes the best idea, opens a visible Chrome window (`headless=False`), navigates to Google Gemini, activates the Deep Research mode, injects the master prompt, and clicks "Start research" (`Recherche starten`).

### 2. High-Fidelity UI Extraction (Clipboard Method)
To extract perfectly formatted Markdown (including tables and bold text) from the completed Gemini Deep Research report, the extraction engine now utilizes a UI-driven Clipboard approach:
- The script automatically scrolls to the bottom and clicks the **"Teilen und exportieren"** (Share) button.
- It clicks **"Inhalte kopieren"** (Copy).
- It extracts the Markdown directly via `navigator.clipboard.readText()`.
- *Fallback:* If the UI changes, it safely falls back to standard DOM scraping.

### 3. The "Synthetic Blood" Testing Strategy
To test the complex browser automation without exhausting Google Custom Search quotas or getting blocked by Reddit/G2:
- The real-world web scraping loop in `run_venture_analyst.py` (`[1/3] FIELD RESEARCH`) can be temporarily commented out.
- This forces the system into a fallback mode where it injects **"Synthetic Pain"** (hardcoded, high-quality sample data like paralegal frustrations).
- The pipeline processes this dummy data in seconds and immediately triggers Phase 4, allowing rapid testing of the Gemini UI automation.

### 4. API Key Rotation & Infinite Rate-Limit Cooldown
- The system heavily relies on `gemini-2.5-flash` for the agentic processing. 
- To prevent rate-limiting and quota exhaustion (`429` errors), `src/core/secret.py` contains a robust thread-safe key-rotation mechanism.
- **Update (March 9, 2026):** Implemented an "Infinite Cooldown Loop". If all keys hit the Google Free-Tier Rate Limits (429), the system dynamically parses the required waiting time from the error message (e.g., "retry in 49s") and pauses the pipeline for that exact duration instead of crashing. This ensures zero data loss during massive batch extractions.

### 5. Smart DOM-Polling for Browser Automation (March 9, 2026)
- The Deep Research Browser Extraction (`src/modules/browser/provider.py`) was upgraded from a rigid time-based wait to intelligent DOM-Polling.
- The script actively checks if Gemini is still generating (by looking for the Stop button) and waits until the exact "Teilen und exportieren" button appears before attempting to copy the Markdown from the clipboard. This eliminates premature aborts and "False Positives" on similar icons.

### 6. Robust Dynamic Polling for Deep Research (March 10, 2026)
- The Playwright automation for Gemini Deep Research was enhanced with an aggressive, continuous scrolling and multi-selector polling loop (`src/modules/browser/provider.py`). This resolves a critical bug where the automation would hang indefinitely if the generation of the initial research plan took longer than 15 seconds or if Google slightly altered the DOM structure of the "Start research" button.

---

## 🚀 Open To-Dos & Future Explorations (March 10, 2026)

- [ ] **Electron App / GUI:** Build a graphical user interface (e.g., via Electron) to make the system more intuitive to operate and to easily select specific research templates/use cases.
- [ ] **Sandbox / VM Isolation for Agents:** Investigate running browser agents inside VMs or Docker containers (similar to OpenClaw recommendations on Mac Minis) to prevent the automated browser windows from interfering with the main Windows machine during background execution.
- [ ] **Deep Research Templates:** Create predefined templates and structures for Deep Research so that users don't have to manually craft complex prompts. This could be integrated into the GUI for easy use-case selection.
- [ ] **Autonomous App Generation Workflow:** Evolve the system to act autonomously (e.g., via MCP or as a master agent) to automatically generate code, scripts, or prototype apps based on the identified market gaps and research memos.
- [ ] **Cloud LLM Integration & Context Management:** Better integrate cloud LLMs (taking advantage of generous rate limits) by creating a dedicated project-based chat in Google AI Studio. This chat could act as the project's memory, receiving terminal outputs, progress updates, screenshots, or even video recordings of the agents to maintain deep context over time.
- [x] **Global Research Database:** Track all researched use cases, ideas, and analyzed problems across different Deep Research runs in a massive, structured database or table. This should include metadata like ratings, key metrics, dates, and industries, allowing the system to know what has been researched and triggering re-evaluations when technologies or markets shift.
- [ ] **Iterative Prompt Template Creator (Research Expansion):** Expand the scope of the repo from just "Venture Research" to general "Research Automation". For example, build an iterative prompt optimization engine where one LLM generates prompt templates, another tests them across various Cloud LLMs, validates the outputs, and feeds feedback back until highly optimized, use-case-specific prompt templates are finalized into a reusable library.

### 💡 Additional AI Proposals for the Roadmap
- [ ] **Automated Repo Scaffold & Issue Creation:** Once a validated Venture Memo is generated and scores above a certain threshold, automatically initialize a new GitHub repository, populate it with the memo, and generate a scaffolded project structure.
- [ ] **Multi-Persona Browser Profiles:** Implement a robust profile manager to allow agents to simulate different user personas (e.g., "Developer", "Compliance Officer", "Teenager") with distinct browsing histories and cookies, to gather unbiased or perspective-specific search results.
- [ ] **Agentic Social Media Listening:** Instead of waiting for a manual keyword search, have a background agent continuously monitor platforms like Reddit, Hacker News, or Twitter for spikes in specific pain-point keywords and trigger the Venture Pipeline automatically when signal density is high enough.
