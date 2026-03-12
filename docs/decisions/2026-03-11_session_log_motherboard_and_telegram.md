# Session Log: 11. März 2026 - Das Motherboard & Der Schritt zur Fernbedienung

**Zusammenfassung der heutigen Architektur-Entwicklungen und Implementierungen.**
*Dieses Dokument dient als Kontext-Anker für zukünftige Agenten-Sessions.*

## 1. Was heute erfolgreich gebaut wurde (Phase 2-4 abgeschlossen)
Wir haben die isolierten Agenten-Skripte in eine echte "Agentic Workflow"-Architektur (das "Motherboard") überführt:
*   **Tool Registry (`src/core/registry.py`):** Ein zentrales System, das Tools über Pydantic-Schemas validiert und registriert.
*   **Der Local Router (`src/agents/local_router/router.py`):** Ein semantischer Router, der natürliche Sprache empfängt und über Ollama (`qwen3:8b`, via `format="json"`) fehlerfrei in maschinenlesbare Tool-Befehle (JSON) übersetzt.
*   **Der Async Orchestrator (`runs/orchestrator.py`):** Das asynchrone Main-Loop-Skript. Es nutzt `aioconsole.ainput` für nicht-blockierende Eingaben und fängt synchrone Tools (wie den CV-Bot, der PyAutoGUI nutzt) sicher über `asyncio.to_thread` ab, damit der Event-Loop niemals einfriert.
*   **Deep Research Entkopplung:** Wir haben das Gemini Deep Research Modul (via Playwright) aus dem Venture-Analysten extrahiert und als eigenständiges, unabhängiges Tool `gemini_deep_research` registriert.

## 2. Architektonische Entscheidungen & Hardware-Vision
Wir haben eine strategische Debatte über die Hardware-Zukunft des Projekts geführt und die Ergebnisse in `docs/decisions/02_router_scaling_and_cloud_strategy.md` dokumentiert:
*   **Hardware:** Obwohl ein Mac Mini M4 technisch ideal wäre, lautet die Anweisung des Product Owners: **Zero-Cost & Vendor-Lock-in vermeiden**.
*   **Die Zukunft (Cloud):** Wenn das System auf einen Cloud-Server (ohne GPU) umzieht, werden wir das lokale Ollama-Modell durch kostenlose APIs (Gemini Flash, Groq) ersetzen (Model Cascading).
*   **Das CV-Bot Problem:** In einer Headless-Cloud-Umgebung wird die "Sight & Touch" Architektur (PyAutoGUI) nicht funktionieren. Diese Tools werden dann durch API-gesteuerte Scraper (Browserless, Firecrawl) ersetzt.

## 3. Aktueller Status (Startpunkt für die nächste Session)
Wir haben das "Epic 03: Telegram Bot Interface" gestartet. Der Plan dafür liegt in `docs/plans/03_plan_telegram_bot.md`.
*   **Phase 1 (Bot Setup & Security) ist programmiert.** Der Code liegt in `runs/telegram_bot.py`. Er enthält harte Security-Checks (`ALLOWED_TELEGRAM_USER_IDS`).
*   **NÄCHSTER SCHRITT (Handoff an User/Next Agent):**
    1.  User muss bei Telegram (@BotFather) einen Bot erstellen und seine eigene User-ID herausfinden.
    2.  User muss lokal `pip install python-telegram-bot python-dotenv` ausführen.
    3.  User muss eine `.env` Datei im Root-Verzeichnis anlegen (`TELEGRAM_BOT_TOKEN=...` und `ALLOWED_TELEGRAM_USER_IDS=...`).
    4.  User führt `python runs/telegram_bot.py` aus und schreibt dem Bot in Telegram "Ping".
    5.  Wenn der Bot mit "Pong!" antwortet (Quality Gate Phase 1 bestanden), startet der nächste KI-Agent direkt mit **Phase 2 (Router-Integration)** im Plan `03_plan_telegram_bot.md`.
