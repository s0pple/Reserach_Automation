# Plan: 03 - Telegram Bot Interface (Der Controller)

**Status:** Draft / Review
**Ziel:** Steuerung der Research Automation Pipeline (Venture Analyst & CV-Bot) nicht mehr über das lokale Terminal, sondern bequem per Telegram von überall.

## 🏗️ Architektur-Entscheidung: Warum ein Telegram Bot?
Die Frage war: "Heißt das nicht, dass unser Python-Programm die ganze Zeit laufen muss wie mein PC?"
**Antwort:** Ja, absolut. Solange die Architektur "Local-First" ist (und Tools wie der CV-Bot deine lokale Maus steuern oder Ollama auf deiner GPU läuft), muss dein PC und das Skript laufen. 
**Warum Telegram trotzdem der logischste Schritt ist:**
1. **Entkopplung:** Du bist nicht mehr an deinen Monitor gefesselt. Du kannst den PC morgens anlassen, gehst zur Arbeit und schreibst auf dem Weg in Telegram: `Mache eine Marktanalyse über AI im Bauwesen`. Der PC zuhause rattert los und schickt dir 5 Minuten später das fertige PDF/Markdown aufs Handy.
2. **Cloud-Readiness:** Wenn wir die Pipeline später (wie im vorherigen Plan besprochen) auf einen Hetzner-Server schieben, läuft das Skript dort 24/7. Du brauchst dann ohnehin ein User-Interface (UI). Ein Telegram-Bot ist das mit Abstand schnellste, sicherste und stabilste UI für Text-basierte KI-Agenten, für das wir keine Frontend-App programmieren müssen.

---

## 🛠️ Geplante Architektur & Datenfluss

```text
[Telegram App (Handy)] 
       │
       ▼ (python-telegram-bot / async)
[runs/telegram_bot.py] ───(Leitet Nachricht weiter)───▶ [src/agents/local_router/router.py]
       │                                                         │
       │ (Wartet & Streamt Updates)                              ▼ (JSON Intent)
       │                                                         │
       ◀────────────────────────────────────────────── [ToolRegistry (Venture/CV)]
       │ (Fertiges Markdown als File-Upload)
```

---

## 📅 Phasen-Plan (Umsetzung)

### Phase 1: Bot-Setup, Skeleton & Security
- **Ziel:** Die asynchrone Grundstruktur des Bots aufsetzen, der exklusiv auf autorisierte Nutzer reagiert.
- **Aufgaben:**
  - `python-telegram-bot` zu den `requirements.txt` hinzufügen.
  - `runs/telegram_bot.py` erstellen.
  - Den asynchronen Main-Loop (`ApplicationBuilder`) implementieren.
  - Eine `.env`-Datei für `TELEGRAM_BOT_TOKEN` und `ALLOWED_TELEGRAM_USER_IDS` (kommasepariert) integrieren.
  - Sicherheitsprüfung in jedem Handler: `if str(update.effective_user.id) not in ALLOWED_IDS: return`.
  - Einen simplen Echo-Test: Wenn User "Ping" schreibt, antwortet Bot "Pong".
- **Quality Gate:** Führe `python runs/telegram_bot.py` aus. Sende eine Nachricht von einer nicht-autorisierten ID -> keine Antwort. Sende "Ping" von der eigenen ID -> Bot antwortet "Pong".

### Phase 2: Die Router-Integration (Das Gehirn anschließen)
- **Ziel:** Telegram-Nachrichten an das LLM (Ollama) weiterleiten.
- **Aufgaben:**
  - Importiere `analyze_intent` und die `ToolRegistry`.
  - Wenn eine Nachricht ankommt, sende temporär "⏳ Analysiere Befehl..." an den User.
  - Führe `analyze_intent(message)` aus.
  - Antworte dem User mit der Entscheidung: "⚙️ Führe Tool XYZ aus mit Parametern ABC".
- **Quality Gate:** Sende "Analysiere den Markt für AI". Der Bot muss den JSON-Intent (Tool `venture_analysis`) im Chat als Text antworten.

### Phase 3: Asynchrone Tool-Ausführung & Error Handling
- **Ziel:** Die Tools nicht blockierend starten und Status-Updates in Telegram sichtbar machen.
- **Aufgaben:**
  - **Architektur-Vorgabe:** Verändere NICHT den Kerncode der Tools! Baue stattdessen in `telegram_bot.py` einen Wrapper (`asyncio.create_task` oder Background-Tasks), damit der Bot nicht blockiert.
  - Für Feedback: Fange temporär `sys.stdout` ab oder leite Logging-Meldungen ab einem bestimmten Level an den Chat weiter (optional, ansonsten reicht ein "Start..." und "Fertig...").
  - **Fehlerbehandlung:** Umschließe die Tool-Ausführung strikt mit `try/except`. Sende dem User bei Abstürzen zwingend eine Fehler-Nachricht (z.B. "❌ Fehler: [Message]").
- **Quality Gate:** Triggere den Venture Analyst. Sende direkt danach "Ping". Der Bot muss mit "Pong" antworten, *während* im Hintergrund noch das Tool läuft (kein Blockieren des Event-Loops).

### Phase 4: File-Upload (Das finale Memo)
- **Ziel:** Das fertige Markdown-Dokument aufs Handy liefern.
- **Aufgaben:**
  - Sobald `venture_analysis` oder `gemini_deep_research` fertig ist, nimm den zurückgegebenen Dateipfad (`result.get("file")`).
  - Nutze `context.bot.send_document()`, um das File direkt als Anlage in den Chat zu laden.
- **Quality Gate:** Nach Abschluss eines Research-Befehls muss die `.md`-Datei im Telegram-Chat zum Download bereitstehen.

---

## ❓ Offene Fragen zur Klärung (Manager & User)
1. **Security:** Sollen wir eine "Allowed Users"-Liste einbauen, damit nicht jeder auf Telegram deinen Bot finden und deinen PC fernsteuern kann? (Ich empfehle dringend ein einfaches Array mit deiner `USER_ID` im Code).
2. **Freigabe:** Bist du mit diesem Plan einverstanden? Sollen wir mit Phase 1 starten?
