# Plan 05: Der CLI-Session-Manager (Phalanx Terminal Multiplexer)

**Status:** Draft 📝
**Ziel:** Langlebige, interaktive CLI-Sessions (insbesondere für KI-Agenten wie die Gemini-CLI) direkt aus Telegram heraus asynchron starten, steuern und überwachen.

---

## 📖 User Story (Die "Vom Bett aus"-Vision)

**Als Oliver** möchte ich abends im Bett über Telegram schreiben:
*"Starte eine neue Gemini-CLI Session im Projektordner X. Sag ihr, sie soll das Refactoring von Datei Y machen und melde dich, wenn sie fertig ist oder eine Rückfrage hat."*

**Der Phalanx-Bot (Orchestrator) antwortet:**
*"🚀 Session `gemini_refactor_1` gestartet. CLI läuft im Hintergrund. Ich melde mich."*

*(10 Minuten später vibriert das Handy)*
**Phalanx-Bot pusht eine Nachricht:**
*"⚠️ **Session `gemini_refactor_1` braucht Input:**
`[Gemini CLI]: Ich habe Datei Y umgebaut, aber Tests schlagen fehl. Soll ich versuchen, den Code selbst zu heilen? [y/N]`"*

**Oliver schreibt in Telegram:**
*"Antworte der Session `gemini_refactor_1` mit `y`."*
(Oder kürzer, weil der Router den Intent versteht: *"Ja, mach weiter in der Refactor-Session"*).

**Phalanx-Bot (Orchestrator):**
*"Eingabe `y` an Session `gemini_refactor_1` gesendet. Warte auf Output..."*

---

## 🛠️ Architektur & Technologie-Stack

### Die Herausforderung: Das "Hängende Terminal"
Standard-Subprozesse (`subprocess.run` oder das aktuelle `cli_tool`) warten, bis ein Befehl fertig ist (EOF), und geben dann den gesamten Text zurück. Interaktive CLIs (wie Gemini-CLI, npm init, etc.) blockieren aber den Prozess, weil sie auf `stdin` (User-Input) warten, während sie noch nicht beendet sind.

### Die Lösung: `asyncio.subprocess` (Pipes) + Background Tasks + In-Memory Registry

Wir bauen eine eigene Mini-Version von `tmux`/`screen` in Python, die speziell für asynchrone Telegram-Kommunikation optimiert ist.

**Technologien:**
1.  **Python `asyncio.subprocess.PIPE`**: Um die Standard-Eingabe (`stdin`) und Ausgabe (`stdout`/`stderr`) kontinuierlich zu streamen, ohne zu blockieren.
2.  **In-Memory Session Registry (`Dict[session_id, SessionObject]`)**: Speichert alle aktiven Sessions. Wenn der Telegram-Bot abstürzt, sind die Sessions aktuell verloren (für MVP OK, später evtl. auf benannte `tmux`-Sessions umsteigen).
3.  **Telegram Async Callbacks**: Der Bot übergibt dem Session-Manager eine `send_message(text)` Callback-Funktion, damit der Manager von sich aus (Push) Nachrichten schicken kann, wenn neue Textblöcke von der CLI kommen.

---

## 🗺️ Phasen der Umsetzung

### Phase 1: Die Session-Tool API (Das Backend)
*   **Input (vom Router):** JSON mit `action` ("start", "input", "read", "kill"), `session_id`, `command` (für "start"), `input_text` (für "input").
*   **Output (an Orchestrator):** JSON mit Status (`success`, `session_id`, `message`).
*   **Mechanismus:**
    *   Wir bauen ein `src/tools/general/session_tool.py`.
    *   Es enthält eine Klasse `SessionManager`, die `asyncio.create_subprocess_shell` nutzt.
    *   Ein dedizierter Background-Task (Daemon) liest *permanent* von `stdout` des Prozesses (`await process.stdout.read(1024)`).
    *   Wenn nach einer kurzen Verzögerung (z.B. 1-2 Sekunden Stille) Text gelesen wurde, wertet der Manager dies als "Die CLI wartet jetzt" und feuert den Telegram-Callback mit dem Puffer-Inhalt ab.

### Phase 2: Schema & Router Integration (Das Gehirn)
*   **Input:** Natürliche Sprache von Telegram.
*   **Mechanismus:**
    *   In `src/schema/tool_parameters.py` definieren wir `SessionActionParams` (mit Literal für start, input, kill).
    *   Der Qwen-Router wird so gepromptet, dass er versteht: "Wenn Oliver eine *laufende* Session erwähnt, nutze Aktion input. Wenn er etwas Neues *interaktiv* starten will, nutze Aktion start."

### Phase 3: Bot.py Refactoring (Die Dynamische Brücke)
*   **Mechanismus:**
    *   Wir schmeißen die harte `if-else`-Logik aus `bot.py` raus.
    *   Wir injecten eine `telegram_callback` Funktion als Parameter in die Tool-Aufrufe, damit Tools (wie das Session-Tool) asynchron Nachrichten in den Telegram-Chat pushen können, ohne dass `bot.py` darauf "warten" muss.

### Phase 4 (Zukunft): AI Studio / Browser-Loop Integration
*   Wenn das CLI-Session-Tool stabil läuft, bauen wir ein "Brücken-Tool". Dieses Tool liest den Output der CLI-Session, übergibt ihn an das Browser-Modul (Playwright), öffnet AI Studio, pastet den Error/Output rein, wartet auf die Antwort des LLMs dort, und leitet die Antwort automatisch wieder als `stdin` in die laufende CLI-Session. (Volle "Self-Healing" Schleife via Web-UI).
