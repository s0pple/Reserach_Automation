# Plan 04: Phalanx 3.0 - OpenClaw, aber brutal (Pragmatische Architektur)

**Status:** In Progress 🚀
**Ziel:** Ein radikal vereinfachtes, kostenloses (Local-First) und modulares System. Keine abstrakte Philosophie, sondern ein System, das sich anfühlt wie ein Chat mit einem intelligenten OS.

---

## Phase 1: Das lokale Gehirn (Zero-Cost Orchestrator)
- **Ziel:** Telegram (`bot.py`) wird komplett dumm. Es nimmt nur Text an und schickt ihn an `router.py`.
- **Mechanismus:** Der `local_router` (angetrieben von unserem lokalen, kostenlosen Qwen-Modell) ist der Orchestrator. Er entscheidet *nur*, welches Tool aufgerufen wird, und extrahiert Parameter.
- **Warum:** So bleibt jede Interaktion, die keine externe Recherche erfordert, 100% kostenlos und extrem schnell. Das `if-else`-Chaos im Bot verschwindet.

## Phase 2: Standardisierung der Tools (Die "Claw-API")
- **Ziel:** Alle unsere bestehenden Scripts (Venture Analyst, CV-Bot, Web-Searcher) erhalten die exakt gleiche Input/Output-Struktur.
- **Mechanismus:** Jedes Tool wird eine Klasse oder Funktion mit einer einheitlichen `execute(params)` Methode, die strikt ein JSON/Markdown zurückgibt. **Kein Tool darf mehr direkt mit Telegram kommunizieren** (kein `update.message.reply_text` in den Tools!).

## Phase 3: Der asynchrone Dispatcher (Hintergrund-Jobs)
- **Ziel:** Langlaufende Recherchen blockieren nicht den Bot oder den Router.
- **Mechanismus:** Wenn der Router entscheidet "Das dauert länger" (z.B. Venture Pipeline), packt er den Job in eine Queue (oder startet einen Background-Prozess). Telegram bekommt sofort die Antwort: "🚀 Job gestartet. Ich melde mich." Wenn das Tool fertig ist, pusht es das Ergebnis aktiv an Telegram zurück.
