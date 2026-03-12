# Architecture Guideline: The God Container (Docker-Inception)

**Date:** March 12, 2026
**Status:** Implemented & Active

## 1. Was ist der "God Container"?
Um KI-Agenten maximale Autonomie zu gewähren, ohne das Host-System (Windows) zu gefährden, haben wir das Konzept der "Zwei-Klassen-Sandbox" durch den "God Container" ersetzt.

Anstatt das Gemini-CLI auf Windows zu starten und Befehle mühsam in einen isolierten Docker-Container (`research_cv_agent`) zu funken, haben wir **das CLI selbst in den Container verfrachtet**.

### Die Architektur-Vorteile:
- **Lokaler Kontext:** Die KI läuft nativ auf Ubuntu/Linux. Sie hat Root-Rechte und kann fehlende Pakete via `apt-get` selbst installieren.
- **Isolierte Ausführung:** Alle Shell-Befehle, Dateioperationen und UI-Tests (Computer Vision, Playwright) passieren im abgesicherten RAM des Containers.
- **Virtueller Monitor (`xvfb`):** Der Container besitzt einen unsichtbaren 1920x1080 Monitor. PyAutoGUI und OpenCV können so GUI-Tests und Browser-Automatisierung ohne echten Bildschirm durchführen (verhindert Fokus-Diebstahl durch Windows).

## 2. Die persistente Spiegelung (Volume Mounts)
Der Container ist so konfiguriert, dass er als reines "Ausführungs-Gehirn" fungiert, seine Daten aber sicher auf dem Windows-Host liegen.

Laut `docker-compose.yml` sind zwei entscheidende Volumes gemountet:
1. `- .:/app`: Spiegelt den gesamten Projektcode (`Research_Automation`) in den Container. Wenn die KI im Container eine Datei in `/app` ändert, wird sie sofort im Windows-Ordner gespeichert.
2. `- C:/Users/olive/Downloads/gemini-cli-main/gemini-cli-main:/gemini-cli-custom`: Spiegelt den *lokal modifizierten* Source-Code des Gemini-CLIs in den Container. Dadurch profitiert die KI im Container von allen Custom-Tweaks (z.B. API-Key-Rotation, Custom Prompts), ohne auf Standard-Images angewiesen zu sein.

## 3. Der Workflow (Starten & Nutzen)

### Container-Lebenszyklus ("Nutzvieh vs. Haustier")
- Der Container läuft als Daemon im Hintergrund (`restart: always`). Sobald Docker auf Windows startet, läuft der unsichtbare Linux-Server.
- Manuelle Installationen (`apt-get install`) bleiben erhalten, solange der Container existiert. 
- **Goldene Regel:** Wenn ein Paket dauerhaft benötigt wird, MUSS es in die `Dockerfile.cvbot` eingetragen und mit `docker-compose up -d --build` neu gebacken werden.

### Wie man die Matrix betritt
Um mit der KI im Container zu arbeiten, wird das Start-Skript über einen Terminal-Exec-Befehl von Windows aus getriggert:

```bash
docker exec -it research_cv_agent /app/start_ai_mode.sh
```

**Was dieses Skript tut:**
1. Prüft, ob der virtuelle Monitor (`xvfb`) läuft.
2. Wechselt in das modifizierte CLI-Verzeichnis (`/gemini-cli-custom`).
3. Installiert fehlende Node-Module (`npm install / build`), falls sie beim Start fehlen.
4. Führt `npm start` aus und bootet die interaktive Gemini-Konsole.

### Authentifizierung im Container
Da der Container headless ist, führt `Login with Google` oft zu "localhost-Routing-Fehlern" im unsichtbaren Browser. 
**Die Lösung:** Wenn eine frische Authentifizierung im Container nötig ist, wähle `Option 1` im CLI-Menü, kopiere den angezeigten Link, öffne ihn manuell im Windows-Browser, kopiere den dort generierten Token und füge ihn im Terminal des Containers ein. So erbt der Container die Premium-Limits des Haupt-Accounts.