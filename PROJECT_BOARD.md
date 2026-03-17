# 📋 Research Automation - Project Board & Kanban

**Last updated:** March 13, 2026 (The Telegram Victory & Watchtower)
**Philosophy:** "Sight & Touch" Hybrid Architecture. Der God-Container ist die unzerstörbare Basis. Telegram ist das Command Center.

---

## 🏗️ Infrastruktur-Status
- **Environment:** Linux God-Container (Docker + Xvfb) -> **STABIL**
- **Intelligence:** Lokaler Qwen-Router + Gemini 1.5 Cloud-Brain -> **AKTIV**
- **Authentication:** Persistent Browser Sessions (Google-Login) -> **AKTIV**

---

## 🚀 Roadmap (Vision 2026)

- ### 🛠️ Sprint 3: "Phalanx 3.0 - The Self-Evolving Agent OS"
- **Priority:** Critical | **Tags:** `[Architecture]`, `[Self-Learning]`, `[Discovery]`
- **Status:** [2026-03-15] **Initialer Masterplan (Plan 11) erstellt.**
- **Key Features:** 
  - **UI Discovery Engine:** Autonomes Mapping von Web-Interfaces (z.B. Gemini, LinkedIn).
  - **The Forge (Tool Generator):** Automatisches Erstellen und Speichern von Playwright/CV-Workflows.
  - **Meta-Router:** Intelligentes Switchen zwischen "Tool nutzen" und "Tool bauen".
- **Goal:** Unbegrenzte Skalierbarkeit über jede Webseite ohne manuelles Hardcoding.

- ### 🕸️ Sprint 2: "The Universal Hunter-Gatherer" (General Agent & Phalanx 2.0)
- **Priority:** High | **Tags:** `[Agent]`, `[Infra]`, `[Scaling]`
- **Status:** [2026-03-15] **Phalanx 2.0 ONLINE & ALWAYS-ON.**
  - [x] JobRegistry (SQLite) implementiert.
  - [x] JobLauncher (Display-Hunting, Profile-Shadowing) fertig.
  - [x] Telegram Bot V2 (Universal Intelligence) aktiv.
  - [x] **Phalanx Daemon (Watchdog):** Automatischer Restart-Mechanismus für 24/7 Betrieb etabliert.
- **Next Step:** Fix `/watch` (Screenshot) reliability issues. Optimize LLM routing for multi-tasking. Implement UI Explorer for Gemini/Migros.
- **Goal:** Parallele, isolierte Research-Jobs direkt über Telegram steuern mit 100% Uptime.

### 💼 Venture Analyst Telegram-Integration (Phase 3)
- **Priority:** Medium | **Tags:** `[Venture]`, `[UI]`
- **Goal:** `/venture [URL]` triggert die komplette Multi-Agenten-Prüfung.

---

## ✅ Done
- **Sprint 1: "The Watchtower" (Telegram Live-View):** `/watch` Befehl in Telegram eingebaut. Asynchrones Screenshot-Tool (scrot). "Schwarzer Bildschirm"-Bug gelöst durch explizites Setzen von `headless=False` und `DISPLAY=:99` im Playwright Environment-Context.
- **Telegram Command Center (Phase 2):** Bot ist online, nutzt den Router und den Whitelist-Schutz.
- **Qwen.ai Deep Research Mastery:** Autonome Eroberung von Qwen unter Nutzung von Google-Sessions.
- **QwenResearcher Tool:** Modulares Tool in `src/tools/` zur Generierung von massiven Marktanalysen.
- **CV-Bot Self-Healing (Linux):** Härtetest im Container bestanden. Vision-basierte Lokalisierung funktioniert stabil unter Xvfb.
- **Repo-Cleanup & V2 Architecture:** Skalierbare, Multi-Agent isolierte Struktur aufgebaut (Kein `/runs` mehr, getrennte `/temp/jobs/`).

---

## 🎯 Backlog / Idea Pool
### 🔍 "Deep Recon" Workflow (Google Search + Multi-Page)
- **Priority:** Medium | **Tags:** `[Web-Scraping]`, `[Scale]`
- **Context:** Google-Suche nach Nische -> CV-Bot scannt erste 3 Seiten & extrahiert URLs -> Playwright besucht URLs im Hintergrund -> Gemini Flash erstellt 1-Satz-Zusammenfassung pro Seite.
- **Goal:** Ein komplettes Markt-Mapping in 5 Minuten.

### 🛡️ "Cloud-Consensus" Workflow (Multi-LLM)
- **Priority:** Medium | **Tags:** `[Quality]`, `[Anti-Hallucination]`
- **Context:** QwenResearcher erstellt Basis-Bericht -> Parallel Senden an Gemini 1.5 Pro & Claude 3.5 Sonnet -> "Skeptic Agent" vergleicht Aussagen. Nur bestätigte Fakten landen im Venture-Memo.
- **Goal:** 100% faktenbasierte Research-Qualität.

### 🕸️ "Competitor Spy" Workflow (Visual Landing Page Analysis)
- **Priority:** Medium | **Tags:** `[Vision]`, `[Analysis]`
- **Context:** CV-Bot macht Screenshots von Wettbewerber-Landing-Pages -> Gemini Vision analysiert Design, Pricing und Value Proposition direkt vom Bild.
- **Goal:** Wettbewerbsanalyse ohne jemals ein DOM-Element anfassen zu müssen (Umgehung von Bot-Fallen).

### 📱 "Telegram Command Center" (Fullscan Workflow)
- **Priority:** Medium | **Tags:** `[UI]`, `[Integration]`
- **Context:** Ein Befehl `/fullscan "PropTech Germany"` triggert: Google Recon -> Qwen Deep Research -> Gemini Synthesis.
- **Goal:** Nach 10 Minuten eine PDF oder ein detailliertes Markdown direkt ins Telegram geliefert bekommen.

### 🤖 "Self-Improving Router" (Quality Gate)
- **Priority:** Low | **Tags:** `[Self-Improvement]`, `[Router]`
- **Context:** Alle Router-Entscheidungen werden geloggt. Einmal am Tag bewertet Gemini 1.5 Pro die Logs und gibt Feedback, wo die Tool-Wahl falsch war.
- **Goal:** Der lokale Router wird jeden Tag klüger, ohne Code anpassen zu müssen.

### 🤖 Sprint 3: "The AI Factory" (Auto-Coder Swarm)
- **Priority:** Medium | **Tags:** `[Self-Improvement]`, `[Orchestration]`
- **Context:** Der Orchestrator spawnt Gemini CLI Sub-Agents in isolierten V2-Workspaces (`temp/jobs/`), lässt sie neue Tools/Workflows programmieren, jagt diese durch Quality Gates (Pytest) und übernimmt nur sauberen Code in `src/tools/`.
- **Goal:** Das System baut seine eigenen Tools autonom.

### 📊 Smarte Synthese & Cloud-Refinement
- **Priority:** Medium | **Tags:** `[LLM]`, `[Quality]`
- **Goal:** Große Reports via Gemini 1.5 Pro auf 1 Seite Executive Summary komprimieren.

- **Multi-User Management:** Rollen-System für den Bot (Admin vs. Read-only).
- **Voice-to-Research:** Sprachnachrichten an den Bot schicken, die automatisch transkribiert und recherchiert werden.
- **Auto-App Generation:** Triggere Aider aus dem Telegram-Bot heraus, um erste Code-Prototypen basierend auf dem Research zu bauen.
