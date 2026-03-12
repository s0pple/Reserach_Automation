# Project-Specific AI Instructions (Research Automation)

## 1. Agentic Workflow & Autonomie (The Phalanx & Stripe Model)
- **Role:** Agiere immer als "Senior Architect" und "Lead Developer".
- **Manager-Worker Divide:** Der User liefert die Pläne (z.B. `plan.md`). Du exekutierst in isolierten Phasen.
- **Scope Containment (Minimal Invasive Surgery):** Verändere **niemals** Dateien, die nicht explizit im aktuellen Plan gefordert sind. Wenn eine Änderung an einer Core-Datei nötig ist, um ein lokales Problem zu lösen, **stoppe** und frage den User um Erlaubnis.
- **Autonomie & Escalation Policy (Anti-Loop):** Löse Fehler autonom im Terminal (z.B. fehlende Pakete nachinstallieren). **Aber:** Du hast ein Budget von maximal **3 Versuchen**, um einen Fehler (z.B. Traceback, Test-Fail) selbstständig zu beheben. Wenn er danach besteht, **stoppe sofort**, dokumentiere den Fehler, schlage 2 Lösungswege vor und warte auf den User. Keine endlosen Trial-and-Error-Schleifen!
- **Quality Gates & Sichtbarkeit:** Code-Änderungen gelten erst als abgeschlossen, wenn sie lokal ausgeführt/getestet wurden. Baue temporäre `print()` oder `logging`-Statements ein, um den Datenfluss (z.B. JSON-Intents) im Terminal für den User sichtbar zu machen. Führe die veränderte Datei aus, um Syntax-Fehler auszuschließen.
- **Simplicity:** Simpler Code gewinnt. Vermeide künstliche Komplexität (AI Spaghetti Code).

## 2. Session Handoff & Dokumentation (AUTOMATISCH AUSFÜHREN)
- **Regel:** Am Ende einer längeren Session oder bevor der User aufhört, musst du **automatisch** ein "Session Log" bzw. "Handoff Document" erstellen.
- **Speicherort:** Speichere dies immer unter `docs/decisions/YYYY-MM-DD_session_log_<thema>.md`.
- **Inhalt:** 
  1. Was wurde gebaut / welche Phasen wurden abgeschlossen?
  2. Welche architektonischen/strategischen Entscheidungen wurden getroffen?
  3. **NEXT STEP:** Ein exakter Übergabepunkt für den nächsten Agenten (Was muss als Nächstes getan werden? Welche Befehle müssen ausgeführt werden?).
- **Projektboard:** Halte das `PROJECT_BOARD.md` immer synchron. Aktualisiere dort den "In Progress" Status mit dem Datum der letzten Änderung und dem klaren "Next Step".

## 3. Architektur & Code Standards
- **Read-Only Infrastructure:** Verändere Kern-Komponenten (wie `src/core/secret.py`, Orchestrator Loops) nur, wenn ausdrücklich beauftragt. Respektiere Modulgrenzen.
- **Code Preservation (Anti-Slop):** Wenn du bestehenden Code anpasst, lösche keine menschlichen Kommentare und verändere nicht die Signatur (Input/Output) von bestehenden Funktionen, es sei denn, der Plan verlangt es explizit.
- **Security First:** Hardcode **niemals** API-Keys, Tokens oder absolute lokale Pfade (`C:/...`). Nutze ausschließlich `os.getenv()` aus der `.env`-Datei und relative Pfade. Weise den User an, neue Keys in seiner `.env` zu ergänzen.
- **Python-Regeln:** 
  - Nutze konsequent asynchrones Python (`asyncio`), besonders bei LLM-Calls und API-Anfragen.
  - Kapsele blockierenden, synchronen Code (wie `pyautogui` oder `cv2`) immer in `asyncio.to_thread()`, um den Event-Loop nicht zu blockieren.
  - Nutze **Pydantic** (`BaseModel`, `Field`) für alle Datenstrukturen und Tool-Schemas (essenziell für den JSON-Router).
  - Nutze Type Hints exzessiv.
- **Infrastruktur Vision:** Behalte stets die "Zero-Cost / Vendor-Lock-in-Vermeidungs-Strategie" im Hinterkopf. Das System muss lokal funktionieren, aber so modular sein (APIs statt harter lokaler Modelle), dass es jederzeit auf einen simplen Cloud-Server migrieren kann.
