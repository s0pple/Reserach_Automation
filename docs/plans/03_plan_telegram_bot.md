# Plan: 03 - Telegram Bot Interface (Der Controller)

**Status:** Phase 2 Completed ✅ / Phase 3 In Progress 🚀
**Ziel:** Vollständige mobile Steuerung des Research Automation Systems.

---

## ✅ Phase 1: Das Skelett (Abgeschlossen)
- [x] BotFather Setup & Token-Handling.
- [x] Whitelist-Security (Nur Oliver darf steuern).
- [x] Docker-Hintergrund-Dienst im God-Container.

## ✅ Phase 2: Die Router-Brücke (Abgeschlossen)
- [x] Integration des lokalen Qwen-Routers.
- [x] Intent-Erkennung (Tool-Selection).
- [x] **Qwen-Power:** Mobile Triggerung von massiven Markt-Berichten.
- [x] Automatisierter Dokumenten-Versand (.md Files).

## 🚀 Phase 3: Die Venture-Pipeline & Synthese (In Progress)
- [ ] **Venture Trigger:** Anbindung der Agenten-Teams (Planner, Collector, Critic) an Telegram.
- [ ] **Live-Protokoll:** Detailliertere Status-Updates während der Venture-Analyse ("Kritiker prüft gerade...").
- [ ] **Smarte Synthese:** Automatisches Post-Processing der Qwen-Berichte via Gemini 1.5 Pro API, um Kurzzusammenfassungen zu generieren.
- [ ] **Visual Feedback:** Der Bot schickt auf Anfrage einen Screenshot vom virtuellen Monitor (:99), damit man sieht, was er gerade "sieht".

---

## 🛠️ Technische Mandate
1. **Async Only:** Keine Blockierung des Telegram-Loops durch lange Web-Scrapes.
2. **Whitelist Hardcoded:** Sicherheit geht vor Feature-Reichweite.
3. **Persistenz:** Alle über Telegram getriggerten Runs müssen in der SQLite DB landen.
