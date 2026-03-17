# Plan 11: Phalanx 3.0 - Self-Evolving Agent OS

## 🎯 Vision
Transformation des Systems von einem statischen Tool-Nutzer zu einer autonomen "Gießerei" (Forge), die neue Web-Interfaces exploriert, Funktionen mappt und dauerhaft wiederverwendbare Toolboxes/Workflows erstellt.

---

## 🏗️ Phasenmodell

### Phase 1: Die Discovery-Phase (UI-Explorer)
- **Ziel:** Autonomes Mapping unbekannter Webseiten.
- **Mechanismus:** Screenshot -> Vision-LLM Analyse -> Element-Identifikation.
- **Output:** `toolbox_<site>.json` (Maschinenlesbare Karte aller Buttons/Inputs).

### Phase 2: Die Forge-Phase (Workflow-Generator)
- **Ziel:** Erstellung ausführbarer Sequenzen.
- **Mechanismus:** LLM schreibt Playwright/CV-Bot Code basierend auf der Toolbox.
- **Output:** `workflow_<site>_<action>.yaml`.

### Phase 3: Der Meta-Orchestrator (Self-Learning)
- **Ziel:** Intelligente Entscheidung: "Nutzen" vs. "Bauen".
- **Mechanismus:** Gap-Analyse triggert autonom Phase 1 & 2 bei unbekannten Anfragen.
- **Resultat:** Das System lernt mit jeder neuen Aufgabe.

---

## 📋 Case Study: Gemini-Integration
1. **Mapping:** `gemini.google.com` wird exploriert (New Chat, Model Toggle, etc.).
2. **Toolbox:** Speicherung als `src/tools/cv_bot/templates/toolboxes/gemini.json`.
3. **Execution:** Bot nutzt diese Toolbox, um autonom in Gemini zu recherchieren.

---

## ✅ Warum dieser Weg? (The Green Strategy)
- **Zero-Maintenance:** Keine manuellen Updates bei UI-Änderungen (Auto-Heal).
- **Infinite Scaling:** Das System ist nicht auf vorinstallierte Tools limitiert.
- **Asset Creation:** Jede explorierte Seite wird zu einem permanenten digitalen Asset in unserer Toolbox.

**Status:** Initialer Entwurf (2026-03-15)
**Next Step:** Implementierung der Forge-Engine (`tool_forge.py`).
