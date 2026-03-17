# Plan 10: The Autonomous Remote Phalanx (Phalanx 2.0)

## 1. Vision
Transformation des God-Containers von einem Single-Task-System in eine skalierbare Multi-Agenten-Infrastruktur. Über Telegram gesteuerte, isolierte Research-Jobs, die in eigenen Sandboxen (Xvfb + Fluxbox + Shadow-Profile) laufen.

## 2. Kern-Architektur

### A. Die Job-Registry (`data/jobs.sqlite`)
Ein zentraler State-Speicher für alle Hintergrund-Prozesse. 
- **Schema:** `job_id`, `topic`, `status` (PENDING, RUNNING, COMPLETED, FAILED, KILLED), `display`, `pid`, `start_time`, `end_time`.
- **Zweck:** Ermöglicht Persistenz über Bot-Restarts hinweg und verhindert verwaiste (Zombie) Prozesse.

### B. Die isolierte Start-Rampe (`src/core/job_launcher.py`)
Ein Python-Wrapper, der pro Job folgendes Setup hochzieht:
1. **Display-Hunting:** Findet den nächsten freien X-Server ab `:100`.
2. **X-Stack:** Startet `Xvfb` UND `fluxbox` (für korrekte Screenshots).
3. **Profile-Shadowing:** Kopiert ein "Golden Master" Browser-Profil (Read-Only) in `/temp/jobs/<JOB_ID>/profile`.
4. **Execution:** Startet `main.py` mit dem Linux `timeout` Utility (Hard-Limit: 45m).
5. **Log-Capture:** Leite `stdout/stderr` in `/temp/jobs/<JOB_ID>/output.log`.

### C. Telegram Interface (Commands)
- `/run <Thema>`: Registriert Job in DB, spawnt `job_launcher.py` via `subprocess.Popen`.
- `/status`: Listet alle aktiven Jobs aus der DB.
- `/watch <JOB_ID>`: Erstellt Screenshot vom spezifischen Display des Jobs.
- `/logs <JOB_ID>`: Sendet die letzten 20 Zeilen des `output.log`.
- `/kill <JOB_ID>`: Sendet `SIGKILL` an die PID und den X-Server-Stack des Jobs.

## 3. Umsetzungsschritte

### Phase 1: Registry & Launcher (Python)
- [ ] `src/core/persistence.py`: SQLite-Schema für Jobs implementieren.
- [ ] `src/core/job_launcher.py`: Logik für Xvfb/Fluxbox/Timeout/Cleanup.

### Phase 2: Bot-Evolution
- [ ] `/run` Kommando implementieren (Non-blocking).
- [ ] `/watch` & `/live` für Multi-Display-Support erweitern.
- [ ] `/kill` Not-Aus implementieren.

### Phase 3: Robuste Profile
- [ ] Erstelle "Golden Profile" (eingeloggt in Google/Qwen/etc.).
- [ ] Implementiere atomares Kopieren (rsync) vor Job-Start.

## 4. Sicherheits-Features & Limits
- **Resource-Gate:** Maximal 5 parallele Jobs.
- **Auto-Cleanup:** Hintergrund-Task löscht `/temp/jobs/` Verzeichnisse > 24h.
- **Watchdog:** Ein Cron-Job prüft alle 5 Min auf PIDs in der DB, die nicht mehr existieren, und markiert sie als FAILED.

---
**Status:** Aktiviert (Phalanx 2.0 Upgrade)
**Datum:** 2026-03-15
