# Session Log: 2026-03-14 - The General Agent "Hunter-Gatherer" Phase 1-3

## 1. Erreichte Meilensteine (What was built?)
- **Strategische Architektur (Plan 08):** Der "General Agent" wurde als ReAct-Agent (Reason -> Act -> Observe) konzipiert.
- **Intent Routing (Phase 1):** Der Telegram-Bot erkennt jetzt universelle Navigationsziele ("Was kosten Bananen?") und routet sie an den `GeneralExecutor`.
- **The Brain (Phase 2):** `src/agents/general_agent/planner.py` implementiert. Nutzt die Gemini API in striktem JSON-Mode für die Planung des jeweils nächsten Schritts.
- **The Engine (Phase 3):** `src/agents/general_agent/executor.py` implementiert. Hybrid-Ansatz:
  - **DOM-Scraping (Playwright):** Schnelle Interaktion mit HTML-Elementen.
  - **Vision-Fallback (CVBotTool + xdotool):** Automatisches Auslösen von Gemini-Vision, falls Playwright Elemente nicht findet. Nutzt echte Maus-Klicks und Tipp-Events auf dem virtuellen Desktop (:99).
- **Telegram Live Status:** Eine Nachricht im Chat wird nun fortlaufend editiert (`context.bot.edit_message_text`), um den aktuellen "Gedankengang" des Agenten anzuzeigen, ohne den Chat zu fluten.

## 2. Strategische & Architektonische Entscheidungen
- **Entscheidung:** Wir haben den Plan verworfen, das "Gehirn" (den Planner) über Web-UI-Scraping zu betreiben (zu fragil). Stattdessen nutzt der Planner die offizielle API (JSON Mode), während der Executor für die echte Datenbeschaffung Web-UIs nutzt.
- **Entscheidung:** Einführung einer `GeneralExecutor`-Klasse, die den State (`current_url`, `last_action_result`) isoliert pro Job hält.

## 3. Bekannte Probleme & Beobachtungen (Lessons Learned)
- **Concurrency Issue:** Der Telegram-Bot scheint den Livestream (`/live`) zu blockieren, während der Agent-Task läuft (oder umgekehrt). Obwohl `asyncio.create_task` genutzt wurde, zeigt der Stream erst nach Ende des Agenten-Tasks wieder Aktivität. Das muss in der nächsten Session über eine bessere asynchrone Struktur im Bot gelöst werden.
- **Vision Reliability:** Beim Test "Bananen bei Migros" schlug Vision fehl ("Could not find Bananen on screen"). Mögliche Ursache: Der Screenshot wurde gemacht, während die Seite noch lud oder ein Pop-up (Cookie-Banner) den Inhalt verdeckte.
- **Rate Limits:** Während der Tests traten Google AI API Rate-Limits auf (429 Quota Exceeded). Das Key-Rotation-System in `secret.py` hat gegriffen, muss aber ggf. auf dem Host-Level großzügiger konfiguriert werden.

## 4. NEXT STEP (Übergabepunkt für die nächste Session)
1. **Concurrency Fix:** Den Telegram-Bot so umbauen, dass `/live` und der Nachrichten-Handler (`handle_message`) wirklich parallel agieren können, ohne sich gegenseitig zu blockieren.
2. **Vision-Debugging:** Den Screenshot-Mechanismus im `GeneralExecutor` verfeinern (z.B. automatisches Schließen von Cookie-Bannern, bevor Vision gerufen wird).
3. **Session Persistence:** Den `GeneralExecutor` so anpassen, dass er das bereits vorhandene `BrowserProfileManager` Profil nutzt, damit wir auf Seiten wie Google/Gemini bereits eingeloggt sind.

---
**Status:** Branch `feat/planning-agent` ist aktiv. Alle Änderungen sind committet.
