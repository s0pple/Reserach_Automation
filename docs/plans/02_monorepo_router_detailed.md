# Plan: 02 - Monorepo & Local Router (Das Motherboard)

**Status:** Ready for Execution
**Ziel:** Zusammenführung isolierter Skripte in eine saubere Monorepo-Architektur. Implementierung eines lokalen LLM-Routers (Ollama), der Befehle entgegennimmt, das Intent als JSON parst und dynamisch an die entsprechenden Tools weiterleitet.

## 🛑 WICHTIGE REGELN FÜR DEN KI-AGENTEN
- Arbeite STRIKT Phase für Phase ab. 
- Beginne niemals eine neue Phase, bevor die vorherige nicht von mir abgesegnet oder erfolgreich getestet wurde.
- Nutze Type Hints (TypeScript/Python typing) exzessiv.
- Wenn du auf Fehler stößt, versuche nicht, die Architektur zu ändern, sondern behebe den Bug im aktuellen Scope.

---

## 🛠 Architektur-Übersicht (Soll-Zustand)

Research_Automation/
├── src/
│   ├── core/              # config.py, registry.py (ToolRegistry)
│   ├── tools/             # cv_bot/, web_scraper/
│   └── agents/            # local_router/, venture_analyst/
├── runs/                  
│   ├── orchestrator.py    # Main Entry Point (asyncio)
│   └── logs/              # session_XXX.jsonl
└── requirements.txt       # Konsolidierte Abhängigkeiten

---

## 📅 Phasen-Plan

### Phase 1: Die Monorepo-Struktur & Dependencies
**Ziel:** Sauberes Refactoring der bestehenden Dateien in die neue Ordnerstruktur.
- [x] Erstelle die oben definierte Ordnerstruktur.
- [x] Verschiebe bestehende Agenten-Skripte nach `src/agents/venture_analyst/`.
- [x] Verschiebe Einstiegsskripte nach `runs/`.
- [x] Passe ALLE relativen und absoluten Imports in den verschobenen Dateien an, damit sie wieder funktionieren.
- [x] Führe alle `requirements.txt` zusammen und speichere sie im Root.

### Phase 2: Tool-Registry mit Pydantic (Die Adapter)
**Ziel:** Standardisiertes Registrieren von Tools für das LLM.
- [x] Erstelle `src/core/registry.py` mit einer Klasse `ToolRegistry`.
- [x] Implementiere `register_tool(name: str, description: str, func: Callable, schema: Type[BaseModel])`. **Wichtig:** Nutze Pydantic BaseModels für das Schema! Das hilft dem LLM später, die Parameter zu verstehen.
- [x] Implementiere `get_tool(name: str)`.
- [x] Lege Dummy-Tools für `cv_click` und `venture_analysis` an, um die Registry zu testen.

### Phase 3: Der Async Local Router & Fallbacks (Ollama)
**Ziel:** Ein Router, der Natural Language in strukturiertes JSON übersetzt.
- [x] Erstelle `src/agents/local_router/router.py`.
- [x] Implementiere `async def analyze_intent(user_command: str, registry: ToolRegistry) -> dict:`
    - Generiere einen dynamischen System-Prompt basierend auf den `descriptions` und `schemas` der Registry.
    - Sende den Prompt an Ollama. **Zwingend:** Nutze `format="json"` in der Ollama API, um garantiertes JSON zurückzubekommen.
    - Erwarteter Output des LLMs: `{"tool": "name", "parameters": {...}}`.
- [x] Implementiere robuste Try/Catch-Blöcke. Wenn Ollama offline ist oder JSON-Parsing fehlschlägt, gib ein Fallback zurück: `{"tool": "error", "message": "..."}`.

### Phase 4: Der Async Orchestrator & Session Logging
**Ziel:** Das asynchrone Main-Loop Skript für den User.
- [x] Erstelle `runs/orchestrator.py`.
- [x] Implementiere einen `asyncio` Event-Loop. 
- [x] **Achtung:** Nutze NICHT das blockierende `input()`. Verwende `aioconsole.ainput()` oder führe den Input in einem ThreadPoolExecutor aus, damit der Event-Loop nicht blockiert wird.
- [x] Implementiere Session-Logging: Speichere jeden Durchlauf (Timestamp, User-Input, Router-Entscheidung, Tool-Status) als Zeile in `runs/logs/session_<timestamp>.jsonl`.

---

## 🧪 Validierung (Quality Gates)
Sobald Phase 4 abgeschlossen ist, muss das System folgende Tests bestehen:

1. **Test 1 (Einfaches Tool):** Eingabe: *"Klicke auf den Warenkorb"* 
   -> Router muss `cv_click` ohne Parameter wählen. Log muss geschrieben werden.
2. **Test 2 (Komplexes Tool mit Parameter):** Eingabe: *"Analysiere den Markt für vertikale Landwirtschaft"* 
   -> Router muss `venture_analysis` wählen und den Parameter `{"domain": "vertikale Landwirtschaft"}` extrahieren.
3. **Test 3 (Resilienz):** Stoppe den Ollama-Service lokal und gib einen Befehl ein. 
   -> Das Skript darf NICHT abstürzen (`Exception` / Traceback), sondern muss dem User elegant antworten: "Lokaler Router nicht erreichbar."