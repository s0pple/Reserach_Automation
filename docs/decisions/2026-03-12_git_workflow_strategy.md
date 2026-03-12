# Git & Backup Strategy (Agentic Workflow Integration)

## Das Problem
In einer komplett autonomen Umgebung ("God Container") haben KI-Agenten Root-Rechte und können in Millisekunden tausende Zeilen Code schreiben oder löschen. Um fatalen Fehlern (Halluzinationen, Löschen falscher Verzeichnisse, versehentliches Überschreiben) vorzubeugen, wird Git als **striktes, deterministisches Sicherheitsnetz** etabliert.

## Die Strategie: "Branch-Driven Agentic Development"
KI-Agenten arbeiten ab sofort NIE wieder direkt auf dem `main`-Branch. Jede Aufgabe wird in einem isolierten Feature-Branch ausgeführt und muss ein "Quality Gate" passieren, bevor sie committet wird.

### Der Workflow (Der 5-Phasen-Loop)

#### 1. Die Mission (Manager / Human)
- Der User vergibt eine neue Aufgabe (z.B. "Baue den Telegram-Controller").
- Die Aufgabe und die Akzeptanzkriterien werden in einem `plan.md` Dokument festgehalten.

#### 2. Der sichere Raum (Worker / Agent)
- Der Agent prüft den Status (`git status`). Ist der Workspace unsauber, bricht er ab und fragt den User.
- Der Agent erstellt einen isolierten Branch:
  ```bash
  git checkout -b feat/telegram-controller
  ```
- Der Agent arbeitet autonom auf diesem Branch.

#### 3. Das Quality Gate & Verification (Worker / Agent)
- Bevor der Agent Code als "fertig" deklariert, **muss** er die Funktionalität prüfen (Ausführen des Skripts, Linter oder Syntax-Check). Der Exit-Code muss `0` sein.
- **Self-Review:** Der Agent führt `git diff` aus und prüft kritisch: *"Habe ich versehentlich Code gelöscht, der nicht zu meiner Aufgabe gehört?"*

#### 4. Der Checkpoint (Worker / Agent)
- Erst nach erfolgreichem Quality Gate und Self-Review macht der Agent den Commit nach Conventional Commits Standard:
  ```bash
  git add .
  git commit -m "feat(telegram): implementiere basis controller logik"
  ```
- Der Agent meldet dem User: "Mission auf Branch 'feat/telegram-controller' abgeschlossen. Bitte auf Windows testen."

#### 5. Die Verschmelzung (Manager / Human)
- Der User testet das Feature.
- Ist alles perfekt, übernimmt der User den Merge:
  ```bash
  git checkout main
  git merge feat/telegram-controller
  git branch -d feat/telegram-controller
  ```

## Fallback: Die "Scorched Earth" Notbremse
Sollte der Agent ein totales Chaos anrichten (kaputter Code + halluzinierte Müll-Dateien), wird der Branch rigoros auf den letzten sauberen Zustand zurückgesetzt.
```bash
git reset --hard HEAD
git clean -fd
```
*(Achtung: `clean -fd` löscht alle neuen, ungetrackten Dateien und Ordner. Das ist der ultimative Undo-Button).*

## Agent Instructions (Zusatz für GEMINI.md)
*Diese System-Regeln sind zwingend bei jedem Aufruf zu beachten:*
1. **Never code on Main:** Prüfe immer mit `git branch`, wo du bist. Erstelle für jeden Plan einen neuen `feat/...` oder `fix/...` Branch.
2. **Review before Commit:** Du darfst **niemals** blind `git add .` ausführen. Du musst vorher `git diff` aufrufen und deine Änderungen verifizieren. Achte besonders auf unabsichtlich gelöschten Code!
3. **Pass the Gate:** Ein Commit erfolgt erst, wenn der Code ausführbar ist und keine offensichtlichen Syntax-Fehler wirft.
4. **Scorched Earth Rollback:** Wenn du dich nach 3 Versuchen in einem fehlerhaften Code-Loop verfängst, nutze `git reset --hard HEAD && git clean -fd`, um deinen eigenen Müll zu beseitigen, bevor du eine neue Herangehensweise planst.