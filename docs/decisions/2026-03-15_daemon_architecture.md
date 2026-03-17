# Architecture Decision Record (ADR): Phalanx Daemon (Watchdog Strategy)
**Datum:** 2026-03-15
**Status:** Aktiviert

## Context
Um das System "immer an" zu halten (ähnlich wie OpenClaw), benötigt der Telegram-Bot eine Infrastruktur, die ihn automatisch startet und bei Abstürzen wiederbelebt, ohne dass ein manuelles Python-Skript im Terminal laufen muss. Da der Container kein `systemd` unterstützt, wird eine Watchdog-Lösung implementiert.

## Entscheidung
Wir nutzen ein Bash-Dämon-Skript (`start_phalanx.sh`), das als langlebiger Hintergrundprozess agiert.

### Mechanismus:
1.  **Dauerschleife:** Prüft alle 30 Sekunden die Prozess-Liste (`pgrep`).
2.  **Auto-Heal:** Wenn `python3 main.py --mode telegram` nicht gefunden wird, wird der Bot sofort neu gestartet.
3.  **Isolation:** Das Skript wird via `nohup` und `disown` vom aktuellen Terminal entkoppelt, damit es auch nach dem Schließen der CLI-Session weiterläuft.

## Konsequenz
Der Bot ist nun "Always-On". Alle Befehle über Telegram werden zuverlässig verarbeitet, auch wenn der Container neu startet oder der Python-Prozess aufgrund eines Netzwerkfehlers abbricht.

---

**Analogie:** Anstatt jedes Mal manuell das Licht einzuschalten, haben wir einen Bewegungssensor mit Dauerlicht-Funktion installiert. Sobald es dunkel wird (Absturz), schaltet sich das Licht (Bot) von selbst wieder an.
