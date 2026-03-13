# Plan: 06 - Memory & Quality Expansion (OpenViking & Promptfoo)

**Status:** Draft / Research
**Ziel:** Das Kurzzeitgedächtnis des God-Containers in ein hierarchisches Langzeitgedächtnis (OpenViking) verwandeln und die Routing-Logik mit automatisierten Tests (Promptfoo) absichern.

## 🏗️ Architektur-Upgrade

### 1. Die Memory-Schicht (OpenViking)
- **Problem:** Aktuell verliert der Orchestrator nach jedem Run den Kontext. CV-Templates liegen verstreut in Ordnern. Research-Ergebnisse sind isolierte Markdown-Files.
- **Lösung:** Implementierung einer hierarchischen Speicherstruktur (L0 Cache, L1 Session, L2 Global Knowledge).
- **Aufgaben:**
    - Analyse der [OpenViking](https://github.com/volcengine/OpenViking) API/Struktur.
    - Integration in `src/core/persistence.py`.
    - Mapping von CV-Templates zu spezifischen "Knowledge Nodes", damit der CV-Bot weiß, welches Template für welches OS/Browser-Konstrukt gilt.

### 2. Der Quality-Gate (Promptfoo)
- **Problem:** Änderungen am System-Prompt des Routers oder ein Modell-Update (z.B. von Qwen zu Llama) können unvorhersehbare Fehler in der Tool-Erkennung verursachen.
- **Lösung:** Automatisierte Evaluation der Prompts.
- **Aufgaben:**
    - Installation von `promptfoo` im God-Container.
    - Erstellung von Test-Suiten für den `local_router`.
    - **Test-Szenarien:**
        - "Analysiere Markt X" -> Sollte `venture_analysis` triggern.
        - "Klicke auf Google Suche" -> Sollte `cv_bot` triggern.
        - Unklarer Befehl -> Sollte `error` mit hilfreicher Nachricht triggern.
- **Integration:** `promptfoo eval` wird zum Teil unseres Deployment-Workflows.

## 📅 Phasen-Plan

### Phase 1: Evaluation (Proof of Concept)
- Lokale Installation der Tools im Container.
- Erster Testlauf mit 5 Standard-Befehlen in Promptfoo.
- Struktur-Entwurf für die OpenViking Datenbank.

### Phase 2: Core-Integration
- Umbau der `persistence.py`, um OpenViking als Backend zu nutzen.
- Anbindung des Routers an die Promptfoo-Test-Suite.

### Phase 3: Self-Optimization
- Der Router nutzt das Langzeitgedächtnis, um vergangene Fehlentscheidungen (via Promptfoo erkannt) in zukünftige Prompts einzubauen (Few-Shot Learning).

---
**Next Action:** Sobald der Telegram-Bot (Phase 1/2) stabil läuft, starten wir mit der Evaluation von Promptfoo für den Router.
