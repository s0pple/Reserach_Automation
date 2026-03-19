# 🏴‍☠️ Geklaute Architektur-Konzepte (OpenClaw & NemoClaw)

Hier sammeln wir die besten Architektur-Patterns von OpenClaw und NemoClaw für unser "The Crucible" / "Förderband" Projekt. Wir übernehmen die cleveren Logik-Konzepte, lassen aber den schweren Node.js/Docker-Overhead weg.

## 1. Prompting & Tools via Markdown (`SOUL.md` & `SKILL.md`)
- **Konzept**: Statt gigantische, schwer lesbare JSON-Schemas für Tools und Agent-Personas zu schreiben, wird reines Markdown genutzt.
- **SOUL.md**: Definiert die Persona, Denkweise (Reasoning) und das genaue Verhalten des Agenten in Textform ("Du bist ein Agent. Denke Schritt für Schritt...").
- **SKILL.md**: Erklärt Tools und ihre Parameter in Markdown. Erklärt dem LLM genau, wann ein Tool fehlschlägt und wie es darauf reagieren soll.
- **Warum**: LLMs "lesen" strukturiertes Markdown oft besser als komplexe JSON-Strukturen, was Halluzinationen reduziert.

## 2. Der dynamische 4-Stufen System-Prompt (`system-prompt.ts`)
Der Prompt des Agenten wird nicht fest reingeschrieben, sondern zur Laufzeit kontextbezogen zusammengebaut. Perfekt für unseren "Self-Healing Fallback":
1. **Rolle & Identität**: Klare, stark limitierte Aufgabe (z.B. "Hochpräziser UI-Recovery Agent").
2. **Aktueller Kontext (dynamisch)**: Was war das Ziel? Was ist der jetzige Fehler? (z.B. `Exception: ElementNotFound`).
3. **Tool/Action Space**: Exakte Liste erlaubter Aktionen (`click`, `type`, `return_to_main_loop`).
4. **Sandbox & Safety**: Harte Grenzen ("Erfinde keine neuen Prozesse", "Klicke Popups weg und kehre zurück").

## 3. Die hybride "Conveyor Belt" Loop (Unser Upgrade zu ReAct)
Klassische Agenten (Sense -> Think -> Act) sind zu langsam. Wir nutzen die "Fließband"-Logik:
```python
def conveyor_belt_loop(workflow_steps):
    for step in workflow_steps:
        try:
            # ⚡ FAST PATH (Dumm, schnell, deterministisch)
            execute_fast_step(step) 
        except Exception as e:
            # 🧠 SLOW PATH (Self-Healing via Vision AI)
            screenshot = take_screenshot()
            prompt = build_healing_prompt(step, e) 
            recovery_action = call_gemini_vision(screenshot, prompt)
            execute_recovery(recovery_action)
            # Danach geht es sofort zurück auf den Fast Path!
```

## 4. Markdown Write-Ahead Logging (Memory Architektur)
- **Konzept**: Vermeidung von teuren und komplexen Vektor-Datenbanken für kurzzeitiges Session-Memory.
- **Umsetzung**: Agenten-Logs und Sessions werden als reine `.md`-Dateien auf die Festplatte geschrieben.
- **Vorteile**: Leichtgewichtig, leicht zu debuggen, perfekt für LLM-Summaries (Context-Compacting) und Notion/Obsidian Export.

## 5. Smart Routing (Inspiriert von NemoClaw)
NemoClaw fängt Tasks ab und routet sie dynamisch. Für uns bedeutet das:
- **Vision-Aufgaben (Self-Healing)** ➔ Weiterleitung an Cloud-Modell (z.B. Gemini 2.5 Flash).
- **Logik / Parsing** ➔ Weiterleitung an lokales Modell (z.B. Qwen via Ollama) für max. Speed & 0€ Kosten.

---
### ⚠️ ERWEITERTE ERKENNTNISSE: Die "Geheimzutaten" für The Crucible

## 6. Der "Specialist Handover" (Micro-Agent Dispatching)
- **Konzept**: Ein einziger Agent wird bei langen Research-Tasks (z.B. "Checke 50 Firmen") irgendwann "müde" (Context-Drift). OpenClaw nutzt "Sub-Souls".
- **Umsetzung**: Der **Main-Router** erledigt keine Arbeit. Er ist nur der Koordinator. Er delegiert an spezialisierte, kurzlebige Worker-Container:
    - `Hunter-Agent`: Findet URLs und LinkedIn-Profile.
    - `Deep-Reader`: Navigiert durch komplexe Webseiten/PDFs via Playwright.
    - `Analyst`: Fasst Daten in das Zielformat (JSON/Markdown) zusammen.
- **Vorteil**: Wenn der `Deep-Reader` in einem Cookie-Banner-Loop stirbt, bleibt der Kontext des `Analysts` sauber. Wir tauschen einfach nur den "kaputten" Worker aus.

## 7. Execution Proofing (Das "Reflexions"-Pattern)
- **Konzept**: LLMs behaupten oft, etwas getan zu haben, ohne es wirklich geprüft zu haben (Halluzination: "Ich habe den Button geklickt").
- **Umsetzung**: Jede `Action` braucht eine `Verification`.
    - *Befehl*: `click("Search")`
    - *Verification*: `wait_for_selector(".results", timeout=2s)` oder `check_cv_match("search_success_indicator")`.
- **The Crucible Logik**: Wenn die Verifikation fehlschlägt, triggert das System sofort den **Slow-Path (Healing)**, anstatt blind den nächsten Schritt im Fließband zu versuchen.

## 8. Session Snapshots & State Restoration (Checkpointing)
- **Konzept**: Research-Tasks dauern oft 15-30 Minuten. Ein Absturz in Minute 14 ist extrem teuer (Zeit & Token). NemoClaw legt Wert auf State-Persistence.
- **Umsetzung**: Nach jedem erfolgreichen Meilenstein (z.B. "Startup-Finanzdaten gefunden") speichert das System:
    1. Den aktuellen DOM-Snapshot.
    2. Die extrahierten Teil-Daten in der `.md`-Datei.
    3. Das aktuelle "Mental Model" des Agenten als Mini-JSON.
- **Vorteil**: Bei einem Timeout oder Crash startet der God-Container neu, lädt den letzten Snapshot und macht exakt dort weiter, wo er aufgehört hat.

## 9. Visual Cropping & Patching (Token-Diät für Vision)
- **Konzept**: Ein voller 1920x1080 Screenshot verbraucht bei Vision-Modellen (Gemini/Claude) viele Token und verwirrt die KI durch zu viele Details.
- **Umsetzung**: Wenn der Fast-Path bricht, schickt der God-Container nicht das ganze Bild an Gemini, sondern:
    1. Einen **verkleinerten Überblick** (Thumbnail) zur Orientierung.
    2. Einen **hochauflösenden Ausschnitt (Crop)** der Region, in der das Element vermutet wird (basierend auf der letzten bekannten Position).
- **Vorteil**: Gemini "sieht" den Button viel schärfer, die Kosten sinken um 70%, und die Genauigkeit der X/Y-Koordinaten steigt massiv.

## 10. Asynchronous Human Intervention (Telegram-Escalation)
- **Konzept**: Vollständige Autonomie ist eine Illusion. Irgendwann kommt ein Captcha oder eine Paywall, die kein Bot knackt.
- **Umsetzung**: Wenn der **Slow-Path (Healing)** nach 3 Versuchen scheitert:
    1. Der Agent schickt einen Hilferuf via Telegram: *"Ich hänge bei Paywall X fest. Bitte hilf mir!"* inkl. Screenshot.
    2. Du klickst in Telegram auf einen Button oder schickst eine Anweisung (z.B. "Überspringe diese Firma").
    3. Der Agent nimmt die Info auf und läuft autonom weiter.
- **Vorteil**: Das Förderband bleibt nicht stehen. Das System "parkt" schwere Fälle und arbeitet den Rest der Liste ab, während es auf deine Antwort wartet.

---

### 🔥 Der "Crucible"-Workflow (Zusammenfassung der neuen Logik)

1.  **Telegram-Input**: Du gibst den Befehl.
2.  **Dispatcher**: Zerlegt den Task in Micro-Jobs.
3.  **Conveyor Belt**: Läuft im God-Container (Fast-Path).
4.  **Verification**: Prüft jeden Klick.
5.  **Healing (Slow-Path)**: Nutzt Gemini + Visual Cropping bei Fehlern.
6.  **Checkpointing**: Schreibt alle 2 Minuten Fortschritte in die `.md`-Memory.
7.  **Escalation**: Meldet sich bei Telegram, wenn es gar nicht mehr weitergeht.

