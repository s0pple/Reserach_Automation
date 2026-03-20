# 🏴‍☠️ Geklaute Architektur-Konzepte (OpenClaw & NemoClaw) & The Crucible Master-Architektur

Hier sammeln wir die besten Architektur-Patterns von OpenClaw und NemoClaw für unser "The Crucible" / "Förderband" Projekt. Wir übernehmen die cleveren Logik-Konzepte, lassen aber den schweren Node.js/Docker-Overhead weg.

## 1. Prompting & Tools via Markdown (`SOUL.md` & `SKILL.md`)
- **Konzept**: Statt gigantische, schwer lesbare JSON-Schemas für Tools und Agent-Personas zu schreiben, wird reines Markdown genutzt.
- **SOUL.md**: Definiert die Persona, Denkweise (Reasoning) und das genaue Verhalten des Agenten in Textform.
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
- **Konzept**: Ein einziger Agent wird bei langen Research-Tasks irgendwann "müde" (Context-Drift). OpenClaw nutzt "Sub-Souls".
- **Umsetzung**: Der **Main-Router** erledigt keine Arbeit, delegiert an spezialisierte Worker-Container (`Hunter-Agent`, `Deep-Reader`, `Analyst`).
- **Vorteil**: Wenn ein Sub-Agent stirbt, bleibt der Haupt-Kontext sauber. Wir tauschen einfach den Worker aus.

## 7. Execution Proofing (Das "Reflexions"-Pattern)
- **Konzept**: LLMs behaupten oft, etwas getan zu haben, ohne es wirklich geprüft zu haben.
- **Umsetzung**: Jede `Action` braucht eine `Verification` (z.B. `wait_for_selector` oder `check_cv_match`).
- **The Crucible Logik**: Wenn die Verifikation fehlschlägt, triggert das System sofort den **Slow-Path**.

## 8. Session Snapshots & State Restoration (Checkpointing)
- **Konzept**: Research-Tasks dauern oft lange. Abstürze sind teuer.
- **Umsetzung**: Nach jedem erfolgreichen Meilenstein wird der DOM-Snapshot, extrahierte Daten und das Zustand-JSON gespeichert.
- **Vorteil**: Neustart am letzten Meilenstein statt komplett von vorn.

## 9. Visual Cropping & Patching (Token-Diät für Vision)
- **Konzept**: Ein voller Screenshot verbraucht viele Token und verwirrt die KI.
- **Umsetzung**: Sende einen verkleinerten Überblick (Thumbnail) und einen hochauflösenden Ausschnitt der vermuteten Region an Gemini.
- **Vorteil**: Höhere Präzision der X/Y-Koordinaten, massive Kostenreduktion.

## 10. Asynchronous Human Intervention (Telegram-Escalation)
- **Konzept**: Eskalation bei unlösbaren Blockern (z.B. Captchas).
- **Umsetzung**: Bei wiederholtem Fehler im Slow-Path sendet der Agent einen Screenshot an Telegram und wartet auf Input (`[Skip]`, `[Remote-Klick]`, `[Manual Override]`).
- **Vorteil**: System "parkt" schwere Fälle und arbeitet den Rest der Liste ab. Das Förderband bleibt nicht stehen.

---

### 🚨 REPO-AI SECURITY & STABILITY WARNINGS (The "Crucible" Flaws) 🚨
*basierend auf der Architekturanalyse des Repo-AIs am 20.03.2026*

**1. Die Async-Hölle: Thread-Pools & Timeouts**
- **Gefahr:** OpenCV `cv2.matchTemplate` ist streng synchron! Wenn wir es im Node-Async-Loop laufen lassen, blockiert der gesamte Orchestrator.
- **Gefahr 2:** Playwright Timeouts. Wenn das Fließband bei einem Fehler auf Telegram wartet, killt der Browser-Prozess den Script nach 30 Sekunden.
- **Fix:** OpenCV MUSS in einen `ThreadPoolExecutor` ausgelagert werden. Playwright-Timeouts müssen beim Aufruf des Human-in-the-Loop dynamisch (`timeout=0`) deaktiviert werden.

**2. Anti-Bot-Flagging bei Web-UIs (z.B. AI Studio)**
- **Gefahr:** Reguläres Playwright wird von Cloudflare gebannt. Session Cookies verfallen random, was den Fast-Path tötet.
- **Fix:** Nutzung von `undetected-chromedriver` oder Playwright-Stealth. Wir MÜSSEN das `user_data_dir` als *externes Docker-Volume* auslagern und eine Wartungs-VNC-Verbindung für regelmäßige, händische Warmup-Logins anbieten.

**3. Docker CV-Diskrepanz (Font-Rendering)**
- **Gefahr:** Templates, die auf Windows gesammelt werden, knallen in der Xvfb-Linux-Umgebung gnadenlos ("Subpixel-Abweichung").
- **Fix:** Templates dürften *ausschließlich* innerhalb des Xvfb-Containers geschnitten werden! Thresholds müssen auf 0.8 / 0.85 gesenkt werden. Wartezeiten einbauen, um CSS-Fade-Ins auszugleichen.

**4. Fehlende Message Queue (Decoupling)**
- **Gefahr:** Die Telegram-Logik ist hart mit dem Web-Scraper verwoben. Ein Telegram-Timeout reißt das Playwright-Script in den Abgrund.
- **Fix:** Einführung einer *einfachen* Queue (oder eines Polling-Filesys-State) zwischen Telegram-Bot und Conveyor Belt. Wenn der Bot Offline geht, wartet das Fließband unbeirrt weiter.

---

# 🔥 Fazit & Synthese: "The Crucible" Master-Architektur

**Projekt-Philosophie:** Baue die asynchrone Spezialmaschine (Assembly Line), nicht das Universal-Betriebssystem.

**Die Crucible Architektur auf einen Blick:**
1. **Das Gehirn:** Markdown-Driven Intelligence (`SOUL.md`/`SKILL.md`) & dynamischer 4-Stufen-Prompt.
2. **Smart Routing:** Lokale LLMs (Qwen) für 90% der Logik, Cloud (Gemini) nur für Vision/Healing.
3. **Das Förderband:** Deterministischer Fast-Path (DOM/OpenCV) + reaktiver Slow-Path (Vision-Fallback) = Hybride `Plan -> Apply` Loop.
4. **Resilienz:** Hooks (`pre_step`/`post_step`), Execution Proofing nach jeder Aktion & Session Snapshotting für Rollbacks.
5. **Gedächtnis:** Vektordatenbank-freies *Markdown Write-Ahead Logging*.
6. **Sicherheit & Kontrolle:** Deklarative Policies (Kosten/Token-Limits) & asynchrone Human-in-the-Loop Eskalation via Telegram bei harten Blockern.

Während Standard-Frameworks wie OpenClaw teure "generalistische Gehirne" sind, die versuchen alles zu steuern, ist The Crucible ein hochoptimiertes Fließband, das sein KI-Gehirn nur als Fallback zuschaltet. Das Resultat: **10x schneller** und **100x günstiger**.

## 11. Decoupling via MCP (Der Microservice-Ansatz)
- **Konzept**: The Crucible (Python/Playwright/CV) wird nicht direkt in OpenClaw (Node.js) integriert, sondern als isolierter **MCP-Server** (Model Context Protocol) oder alternativ als Fake-OpenAI-REST-API betrieben.
- **Umsetzung (MCP)**: Ein lokales, schnelles Modell (z.B. Qwen/Llama 3) in OpenClaw agiert als Orchestrator. Wenn aufwändige Tasks (Web-Research, Reasoning) anstehen, ruft es das MCP-Tool `run_advanced_cloud_research` auf.
- **Vorteil**: Löst die komplette "Asynchrone Hölle". OpenClaw wartet einfach passiv auf den MCP-Response. Der isolierte Python-Docker-Container kümmert sich exklusiv um Browser-Steuerung, Computer Vision (`cv2`) und die asynchrone Telegram-Eskalation (HITL) - völlig getrennt von der OpenClaw Event-Loop.
