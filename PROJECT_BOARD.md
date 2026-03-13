# 📋 Research Automation - Project Board & Kanban

**Date updated:** March 12, 2026
**Philosophy:** "Sight & Touch" Hybrid Architecture. Wir nutzen ein Monorepo. Ein lokales, kostenloses LLM (Ollama) agiert als Router. Komplexe Text/Reasoning-Tasks gehen in die Cloud (Gemini via API/Playwright in Docker). Visuelle Klick-Tasks gehen an den CV-Bot (OpenCV in lokaler VM oder Xvfb Docker).

---

## 🏗️ Architektur & Infrastruktur-Strategie (Die Vision)

1. **Monorepo-Struktur:** Ein einziges Git-Repository. Aufteilung in `src/core` (Gehirn/DB), `src/tools` (CV/Browser), `src/agents` (Venture, Router) und `runs/` (Trigger-Skripte).
2. **Hybrides Routing (Kosten-Optimierung):** 
   - **Router:** Lokales Modell (z.B. Qwen2.5 via Ollama) entscheidet 0€-basiert, welches Tool nötig ist.
   - **Cloud Brain:** Gemini Flash/Pro für schweres Reasoning (Venture Memos, Textanalyse).
3. **The Unbreakable Pipeline (Hybrid Fallback):**
   - **Primär:** Headless Playwright (Millisekunden-schnell, DOM-basiert).
   - **Sekundär (Kavallerie):** Wenn Playwright an Anti-Bot-Mechanismen scheitert, übernimmt der CV-Bot (Menschliche Maus-Simulation via OpenCV/PyAutoGUI).
   - **Tertiär (Self-Healing):** Wenn sich die UI ändert, lernt Gemini (Vision) das neue Interface und heilt den CV-Bot.
4. **OS-Agnostic Isolation (Docker/Sandbox):**
   - Da der CV-Bot sich dank Gemini selbst heilt, ist das Betriebssystem egal. Wir können ihn extrem kosteneffizient in einem Linux-Docker-Container (mit Xvfb für einen virtuellen Monitor) laufen lassen. 

---

## 🎯 Backlog / Idea Pool (Brainstorming)

### 🧠 Autonomous App Generation Workflow
- **Priority:** Medium | **Tags:** `[Agent-Workflow]`
- **Context:** Sobald das Venture Memo steht, baut ein Agent (z.B. Aider) den ersten Code-Prototyp.

### 🧠 Tech Stack Evolution (Future Improvements)
- **Priority:** Medium | **Tags:** `[Infrastructure]`, `[Memory]`, `[Testing]`
- **Context:** Integration von **OpenViking** (hierarchisches Langzeitgedächtnis) und **promptfoo** (automatisierte Quality Gates für den Router).
- **Goal:** Das System muss aus Fehlern lernen und die Zuverlässigkeit der Tool-Entscheidungen messbar machen.

### 🗂️ Template-Management & Ordnerstruktur für den CV-Bot
- **Priority:** Low | **Tags:** `[Refactoring]`
- **Context:** Die gespeicherten Templates müssen strukturiert abgelegt werden (nach Betriebssystem, Browser, Webseite etc.), damit es bei vielen Workflows nicht zu Konflikten kommt.

---

## 🚀 In Progress (Der nächste große Wurf)

### 🖥️ Docker Xvfb-Sandboxing & God Container (Finalisierung)
- **Priority:** High | **Tags:** `[Infrastructure]`
- **Status (13. März 2026):** Der God-Container läuft. Aktuelle Phase: Self-Healing des CV-Bots in der Linux-Umgebung (Google-Suche Workflow). 

### 📱 Telegram Bot Interface (Der Controller)
- **Priority:** High | **Tags:** `[UI]`, `[Trigger]`
- **Context:** Anstatt CLI-Befehle zu tippen, steuern wir den Orchestrator via Telegram-Nachrichten (`/research AI Logistics`).
- **Status (13. März 2026):** Phase 1 vorbereitet. User richtet gerade API-Token & ID ein.
- **NEXT STEP:** Ping/Pong Test & Router-Anbindung (Phase 2).

---

## ✅ Done
- **CV Workflow Recorder & Self-Healing:** OpenCV Fast-Path + Gemini Vision Fallback gebaut und erfolgreich validiert. Kann sich auf jeden beliebigen Screen anpassen.
- **Monorepo & Setup des "Local Routers":** Die bestehende Codebase wurde aufgeräumt. Ein lokaler Router (`orchestrator.py` mit Ollama) leitet Befehle typsicher an Tools (CV-Bot, Venture-Analysis) weiter.
- **Zentrale SQLite Datenbank:** Persistenz für Venture Runs und Memos eingebaut.
- **Robust Dynamic Polling:** Playwright-Wartezeiten für Deep Research flexibel gemacht.
- **The Bridge:** Agent Pipeline triggert erfolgreich das Gemini Deep Research Web-UI.
