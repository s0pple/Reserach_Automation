# Git & Backup Strategy (Agentic Workflow Integration)

## Das Problem
In einer komplett autonomen Umgebung ("God Container") haben KI-Agenten Root-Rechte und können in Millisekunden tausende Zeilen Code schreiben oder löschen. Um fatalen Fehlern (Halluzinationen, Löschen falscher Verzeichnisse) vorzubeugen, muss Git als **striktes Sicherheitsnetz (Undo-Button)** etabliert werden.

## Die Strategie: "Branch-Driven Agentic Development"

KI-Agenten arbeiten ab sofort NIE wieder direkt auf dem `main`-Branch. Jede Aufgabe wird in einem isolierten Feature-Branch ausgeführt. Erst wenn der User (Manager) die Funktionalität verifiziert hat, wird in den `main`-Branch gemerged.

### Der Workflow (Der 4-Phasen-Loop)

#### 1. Die Mission (Manager)
- Der User vergibt eine neue Aufgabe (z.B. "Baue den Telegram-Controller").
- Die Aufgabe wird in einem `plan.md` Dokument festgehalten.

#### 2. Der sichere Raum (Worker / Agent)
- Bevor der Agent auch nur *eine* Codezeile ändert, **muss** er einen neuen Branch erstellen, der nach dem Feature benannt ist:
  ```bash
  git checkout -b feat/telegram-controller
  ```
- Der Agent arbeitet autonom auf diesem Branch (Dateien editieren, Skripte testen, Abhängigkeiten installieren).

#### 3. Der Checkpoint (Worker / Agent)
- Sobald das Feature funktioniert (z.B. der Test-Script-Lauf war erfolgreich), macht der Agent selbstständig einen Commit:
  ```bash
  git add .
  git commit -m "feat: Telegram Controller Phase 1 abgeschlossen"
  ```
- Der Agent meldet dem User: "Arbeit auf Branch 'feat/telegram-controller' abgeschlossen und lokal committet. Bitte auf Windows testen."

#### 4. Die Verschmelzung (Manager)
- Der User testet das Feature auf seinem Windows-System (oder im Container).
- Ist alles perfekt, gibt der User den Befehl zur Verschmelzung (Merge):
  ```bash
  git checkout main
  git merge feat/telegram-controller
  git push origin main
  ```
- Der Feature-Branch kann danach gelöscht werden (`git branch -d feat/telegram-controller`).

## Fallback: Die "Undo"-Notbremse
Sollte der Agent auf seinem Feature-Branch ein totales Chaos anrichten (z.B. Dateien löschen), ist das System sicher. Der User oder der Agent selbst führt einfach aus:
```bash
git reset --hard HEAD
```
Damit wird der gesamte Code sofort auf den Zustand des letzten sauberen Commits zurückgesetzt. Nichts ist verloren.

## Agent Instructions (Zusatz für GEMINI.md)
*Diese Regeln müssen in die System-Prompt (`GEMINI.md`) aufgenommen werden:*
1. **Never code on Main:** Bevor du mit einer neuen Aufgabe beginnst, prüfe mit `git status` auf welchem Branch du bist. Wenn du auf `main` bist, erstelle einen neuen `feat/...` Branch.
2. **Commit often:** Nach jedem erfolgreichen Zwischenschritt (z.B. wenn ein Skript fehlerfrei durchläuft), nutze `git add` und `git commit`, um einen Speicherpunkt zu setzen.
3. **Rollback before loop:** Wenn du einen Fehler nach 3 Versuchen (Anti-Loop-Policy) nicht beheben kannst, setze deinen Code mit `git checkout -- <file>` auf den Ursprungszustand zurück, bevor du den User fragst.