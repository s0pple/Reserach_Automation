# Plan: 01 - Hybrid Architecture & Local Router

**Status:** Draft
**Ziel:** Die Codebase in ein sauberes Monorepo umstrukturieren und den lokalen LLM-Router (Ollama) als zentrales Gehirn etablieren, das zwischen CV-Tools (Klicken) und Cloud-Agenten (Denken) entscheidet.

## Phase 1: Monorepo Restrukturierung
**Ziel:** Eine saubere Trennung von Kernlogik, Werkzeugen und ausführenden Skripten.
1. Erstelle Ordnerstruktur:
   - `src/core/` (LLM-Clients, DB-Verbindungen, Configs)
   - `src/tools/` (Unabhängige Fähigkeiten: `cv_bot/`, `browser_scraper/`)
   - `src/agents/` (Logik-Module: Venture Analyst, Local Router)
   - `runs/` (Die Main-Einstiegspunkte)
2. Verschiebe bestehende Dateien (`run_venture_analyst.py`, `run_research.py`) in den `runs/` Ordner.
3. Integriere den `Fast_Shopping_Bot.py` in `src/tools/cv_bot/`.

## Phase 2: Der Lokale Orchestrator (Router)
**Ziel:** Ein Python-Skript, das Ollama nutzt, um Intents zu verstehen und Tools aufzurufen.
1. Erstelle `src/agents/local_router.py`.
2. Implementiere die Anbindung an die lokale Ollama-API (z.B. Modell: `qwen2.5-coder` oder `llama3`).
3. Erstelle eine `ToolRegistry` (ein Dictionary), das auf die Tools verweist:
   - `run_venture_analysis` -> triggert Gemini Web-Scraping.
   - `execute_cv_click` -> triggert den Fast Shopping Bot.
4. Schreibe den System-Prompt, der das lokale LLM zwingt, ausschließlich JSON mit dem Tool-Namen zurückzugeben.

## Phase 3: Session & Tool Tracking (Das Gedächtnis)
**Ziel:** Nachvollziehen, welcher Agent wann welches Tool benutzt hat.
1. Erweitere die bestehende SQLite-Datenbank (`database.py`).
2. Füge eine Tabelle `SessionLogs` hinzu (Columns: `session_id`, `timestamp`, `agent_name`, `tool_used`, `user_prompt`, `result`).
3. Der `local_router.py` schreibt jeden Entscheid in diese Tabelle.

## Phase 4: Validierung (TDD)
1. **Test 1:** Führe den Router mit "Analysiere den Markt für AI-Zahnärzte" aus. Er muss das Tool `run_venture_analysis` wählen.
2. **Test 2:** Führe den Router mit "Klick auf den Warenkorb" aus. Er muss das Tool `execute_cv_click` wählen.
3. Prüfe die SQLite-Datenbank, ob beide Aktionen geloggt wurden.

---
*Sobald dieser Plan abgenommen ist, beginnen wir mit Phase 1.*