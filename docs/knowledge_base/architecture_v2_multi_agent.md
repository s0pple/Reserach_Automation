# 🏗️ Architecture V2: Multi-Agent & Scale Ready

Diese Architektur ersetzt das alte flache Modell und löst fundamentale Probleme der Skalierbarkeit, Modul-Kollision und Test-Isolation.

## 1. Die Ziel-Architektur (Ordner-Hierarchie)

```text
/app/
├── assets/                 # Statische Ressourcen (Brand, Logos)
├── data/                   # Persistente Daten
│   ├── db/                 # SQLite-Datenbanken (mit Row-Level-Locking)
│   ├── sessions/           
│   │   ├── base_profiles/  # (Read-Only) Master-Profile wie 'google_searcher'
│   │   └── active_jobs/    # (Dynamic) Isolierte Profil-Klone (z.B. /job_987/)
│   └── vectors/            # RAG-Gedächtnis
├── docs/                   # Architektur, Pläne, ADRs
├── infra/                  # Dockerfiles & Xvfb-Setup
├── reports/                # Finaler Output (Memos, Qwen-Reports)
├── src/                    # Der Quellcode (Das Gehirn)
│   ├── core/               # Basis (Secrets, LLM, Registry, Job-ID-Generator)
│   ├── agents/             # Intelligenz (Router, Venture)
│   ├── tools/              # Fähigkeiten (CV-Bot, Web-Scraper)
│   ├── schema/             # Pydantic-DNA (Datenverträge)
│   └── interfaces/         # NEU: Entrypoints & Controller (Ersatz für /runs)
│       ├── telegram/       
│       │   └── bot.py      # Telegram Command Center
│       ├── cli/            
│       │   └── main.py     # Terminal Command Center
│       └── api/            # (Zukünftig) FastAPI Endpunkte
├── tests/                  # Unit- & Integrationstests
├── temp/                   
│   └── jobs/               # NEU: Strikt isolierte Workspaces (z.B. /job_987_screenshots/)
├── .env                    # Secrets
├── PROJECT_BOARD.md        # Kanban
└── main.py                 # NEU: Einziger Root-Entrypoint (Leitet an src.interfaces weiter)
```

---

## 2. Die 3 Harten Architektur-Gesetze

Jeder Agent (und jeder Entwickler), der an dieser Codebase arbeitet, MUSS diese Regeln befolgen:

### Gesetz 1: Multi-Agent State Isolation (Das Anti-Überschreib-Gesetz)
Wenn wir später mehrere Agenten simultan über Docker starten, werden sie sich in `/temp/` und `/data/sessions/` gegenseitig die Profile und Dateien zerschießen, wenn sie auf dieselben Pfade zugreifen.
*   **Korrektur:** Jeder Agent/Task braucht zur Laufzeit seinen eigenen isolierten State.
*   **Implementierung:** Die Ordner `/temp/` und `/data/sessions/` erhalten dynamische Unterordner pro Job-ID (z.B. `/temp/jobs/job_123/` oder `/data/sessions/active_jobs/agent_A/`). Base-Profile (wie `google_searcher`) sind Read-Only und werden für einen Lauf geklont.

### Gesetz 2: Git Worktree & Experiment-Isolation (Das Sandkasten-Gesetz)
Wenn ein Agent im God-Container (mit Root-Rechten) experimentiert (z.B. Self-Healing Skripte testet), darf er niemals direkt im `main`-Branch arbeiten oder dort Dateien überschreiben.
*   **Korrektur:** Neue Workflows oder Experimente finden ausschließlich in separaten Git-Branches statt (z.B. `experiment/vision-fallback-v2`).
*   **Implementierung:** Der Agent muss `git checkout -b` nutzen. Wenn das Experiment scheitert, wird der Branch weggeworfen. Nur bei Erfolg wird zurück nach `main` gemerged.

### Gesetz 3: Modulare Interfaces statt relativer `/runs`-Hölle
Ein `/runs` Ordner für Entrypoints ist ein Anti-Pattern in Python, da er relative Importe (`from src...`) oft bricht und zu `ModuleNotFoundError` führt.
*   **Korrektur:** Entrypoints wie `telegram_bot.py` oder CLI-Starter gehören entweder direkt ins Root-Verzeichnis (als `main.py`) oder sauber verpackt in ein Modul unter `src/interfaces/`.
*   **Implementierung:** Starts erfolgen via `python -m src.interfaces.telegram.bot` oder zentral über eine `main.py` im Root.
