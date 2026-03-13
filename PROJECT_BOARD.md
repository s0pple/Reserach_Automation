# 📋 Research Automation - Project Board & Kanban

**Last updated:** March 13, 2026 (The Telegram Victory & Watchtower)
**Philosophy:** "Sight & Touch" Hybrid Architecture. Der God-Container ist die unzerstörbare Basis. Telegram ist das Command Center.

---

## 🏗️ Infrastruktur-Status
- **Environment:** Linux God-Container (Docker + Xvfb) -> **STABIL**
- **Intelligence:** Lokaler Qwen-Router + Gemini 1.5 Cloud-Brain -> **AKTIV**
- **Authentication:** Persistent Browser Sessions (Google-Login) -> **AKTIV**

---

## 🚀 In Progress (Der nächste große Wurf)

### 🕸️ Sprint 2: "The Hunter-Gatherer" (General Web Surfer)
- **Priority:** High | **Tags:** `[Agent]`, `[Computer-Use]`
- **Context:** Ein generalisierter Web-Agent, der Aufgaben wie "Günstigstes Proteinpulver CH" löst. Sucht via Google, iteriert über Links, extrahiert Daten, vergleicht sie und geht zurück.
- **Goal:** Dynamische Navigation auf unstrukturierten Seiten (ohne fixe Workflows).

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
