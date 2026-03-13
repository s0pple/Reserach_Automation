# 📋 Research Automation - Project Board & Kanban

**Last updated:** March 13, 2026 (The Telegram Victory)
**Philosophy:** "Sight & Touch" Hybrid Architecture. Der God-Container ist die unzerstörbare Basis. Telegram ist das Command Center.

---

## 🏗️ Infrastruktur-Status
- **Environment:** Linux God-Container (Docker + Xvfb) -> **STABIL**
- **Intelligence:** Lokaler Qwen-Router + Gemini 1.5 Cloud-Brain -> **AKTIV**
- **Authentication:** Persistent Browser Sessions (Google-Login) -> **AKTIV**

---

## 🚀 In Progress (Der nächste große Wurf)

### 📊 Smarte Synthese & Cloud-Refinement
- **Priority:** High | **Tags:** `[LLM]`, `[Quality]`
- **Context:** Die Qwen-Reports sind mit 50k-70k Zeichen massiv. Wir brauchen ein Tool, das diese Brocken an Gemini 1.5 Pro schickt, um eine 1-seitige Executive Summary zu erstellen.
- **Goal:** `/research` liefert erst ein kurzes Memo, und das lange File als Anhang.

### 💼 Venture Analyst Telegram-Integration (Phase 3)
- **Priority:** High | **Tags:** `[Venture]`, `[UI]`
- **Context:** Die bestehende Venture-Pipeline (Collector, Analyst, Critic) muss ebenfalls über den Router an den Telegram-Bot angebunden werden.
- **Goal:** `/venture [URL]` triggert die komplette Multi-Agenten-Prüfung.

---

## ✅ Done
- **Telegram Command Center (Phase 2):** Bot ist online, nutzt den Router und den Whitelist-Schutz.
- **Qwen.ai Deep Research Mastery:** Autonome Eroberung von Qwen unter Nutzung von Google-Sessions.
- **QwenResearcher Tool:** Modulares Tool in `src/tools/` zur Generierung von massiven Marktanalysen.
- **CV-Bot Self-Healing (Linux):** Härtetest im Container bestanden. Vision-basierte Lokalisierung funktioniert stabil unter Xvfb.
- **Repo-Cleanup:** Root-Verzeichnis aufgeräumt, Branding in `assets/brand/`, Archivierung alter Tests.

---

## 🎯 Backlog / Idea Pool
- **Multi-User Management:** Rollen-System für den Bot (Admin vs. Read-only).
- **Voice-to-Research:** Sprachnachrichten an den Bot schicken, die automatisch transkribiert und recherchiert werden.
- **Auto-App Generation:** Triggere Aider aus dem Telegram-Bot heraus, um erste Code-Prototypen basierend auf dem Research zu bauen.
