# Session Log: CV Workflow Recorder & Self-Healing Architektur

**Datum:** 12. März 2026

## 1. Was wurde gebaut?
- Implementierung des **CV Workflow Recorders** (`src/tools/cv_bot/workflow_manager.py`).
- **Vision Locator (Lernen):** Wenn ein UI-Element unbekannt ist, macht der Bot einen Panorama-Screenshot, sendet ihn an Gemini 2.5 Flash Vision, und extrahiert die X/Y-Koordinaten (unter Berücksichtigung von Multi-Monitor-Offsets).
- **The Recorder (Gedächtnis):** Ein 50x50 Pixel großer Ausschnitt um den Klickpunkt wird via OpenCV als `.png` Template gespeichert.
- **Fast-Path (Self-Healing Cache):** Bei wiederholten Aufrufen sucht OpenCV lokal blitzschnell nach dem Template (`cv2.matchTemplate`). Nur wenn sich die UI ändert (Template nicht gefunden), wird der teure Vision-Fallback getriggert.
- Aktionen wie `click`, `type`, `hotkey`, `wait` und `extract_clipboard` wurden asynchron via `pyautogui` und `pyperclip` implementiert.

## 2. Architektonische Entscheidungen
- **Die Grenzen der Desktop-Automatisierung:** Tests mit Web-Browsern auf dem Host-System haben gezeigt, dass Fokusverlust (durch Nutzerinteraktion oder Benachrichtigungen) die Extraktion (`Ctrl+A`, `Ctrl+C`) zum Scheitern bringt.
- **Die Hybride Fallback-Pipeline:** 
  Das Web wird standardmäßig mit **Headless Playwright** bedient (schnell, dom-basiert). Scheitert Playwright an Anti-Bot-Schutz oder massiven Layout-Änderungen, greift der **CV-Bot als visuelle Kavallerie** ein. Ändert sich das UI komplett, heilt Gemini das OpenCV-Template. Dadurch wird die Pipeline unzerstörbar.
- **Die OS-Agnostic Docker-Infrastruktur (Veto zurückgezogen):** 
  Weil der CV-Bot über Vision lernt, ist es absolut irrelevant, ob er auf Windows, Mac oder Linux klickt. Die Templates werden bei einem OS-Wechsel einfach einmal neu gelernt. Damit entscheiden wir uns strategisch für **Option 2 (Docker mit virtuellem Xvfb-Monitor auf Linux)**. Das ist hochskalierbar, günstig und cloud-ready.

## 3. NEXT STEP
- **Template-Strukturierung (TODO):** Vorbereitung einer sauberen Ordnerstruktur für `templates/` (nach OS, Tool, Browser, Webseite), um bei der Skalierung im Docker-Container Chaos zu vermeiden.
- **Infrastruktur-Aufbau:** Aufsetzen der Docker-Sandbox-Umgebung (mit Xvfb/VNC) zur gefahrlosen Ausführung von Web- und CV-Workflows, ohne den Host-PC zu stören. Die Gemini CLI Sandbox mit Ordner-Spiegelung bietet hier die perfekte lokale Test-Brücke.
- **Die Orchestrierung (Telegram):** Parallel dazu muss das System über Telegram steuerbar gemacht werden, da ein Headless-Docker-Container zwingend ein Remote-Interface benötigt.