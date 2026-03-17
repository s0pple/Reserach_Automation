# Plan 09: Multi-Agent Concurrency & Isolation (The Phalanx System)

## 1. Problemstellung
Aktuell führt der Start von zwei Gemini-CLI-Instanzen zu Konflikten:
- **Xvfb-Lock:** Beide Instanzen nutzen hardcodiert `DISPLAY=:99`.
- **Browser-Lock:** Playwright kann nicht zwei Instanzen desselben Profils (`browser_sessions/google_searcher`) gleichzeitig öffnen.
- **State-Collision:** Temporäre Dateien in `/temp` werden überschrieben.

## 2. Lösungsansatz: "The Phalanx Isolation"
Wir implementieren eine strikte Trennung pro Prozess (Isolation-by-Default).

### A. Dynamisches Display-Management (Infra-Layer)
- Modifikation von `start_ai_mode.sh`:
  - Sucht das erste freie X-Display (startend bei 99).
  - Erstellt ein dediziertes Lock-File für dieses Display.
  - Startet einen eigenen Window-Manager (Fluxbox) pro Display.

### B. Job-basierte Workspace-Isolation (App-Layer)
- Jeder CLI-Aufruf generiert eine `AGENT_ID` (z.B. `agent_alpha_123`).
- Alle temporären Daten landen in `/temp/jobs/<AGENT_ID>/`.
- **Profile-Shadowing:** Das Master-Browser-Profil wird in den Job-Ordner kopiert (`cp -rp`), dort genutzt und nach Beendigung (optional) zurückgeführt oder gelöscht.

### C. Orchestrator-Update
- Der Orchestrator in `src/core/orchestrator.py` muss `AGENT_ID` als Environment-Variable akzeptieren.
- Tools (wie `cv_bot`) müssen ihre Pfade relativ zur `AGENT_ID` auflösen.

## 3. Implementierungsschritte

### Schritt 1: `start_ai_mode.sh` Refactoring
Script-Logik:
```bash
find_free_display() {
    for i in $(seq 99 110); do
        if [ ! -f "/tmp/.X$i-lock" ]; then
            echo "$i"
            return
        fi
    done
}
```

### Schritt 2: Profile-Shadowing in Python
In `src/modules/browser/profile_manager.py`:
- Methode `get_isolated_profile(job_id)`: Kopiert `google_searcher` nach `/temp/jobs/<id>/profile`.

### Schritt 3: Multi-Terminal CLI Wrapper
Erstellung von `scripts/launch_agent.sh`:
- Kapselt den Startvorgang und weist die `AGENT_ID` zu.

## 4. Erfolgskriterien
- [ ] Zwei Terminals können gleichzeitig `/watch` oder `/research` ausführen.
- [ ] Keine "Target closed" oder "Profile locked" Fehler mehr.
- [ ] Screenshot-Tools (`scrot`) erfassen das korrekte (zugehörige) Display.

---
**Status:** In Planung (2026-03-15)
**Abhängigkeiten:** Architektur V2 (Multi-Agent State Isolation)
