# Docker-Inception: Die ultimative AI-Entwicklungsumgebung

## Ziel
Wir bauen die finale Entwicklungsarchitektur: "The God Container". 
Aktuell läuft das Projekt in einer gespiegelten Windows-Ordner-Struktur, während das Gemini-CLI in seiner eigenen temporären Sandbox sitzt und der Ausführungs-Agent (CV-Bot) in einem separaten Docker-Container (`research_cv_agent`). Das ist zu komplex und limitiert die Autonomie der KI.

Das Ziel ist es, das **Gemini-CLI und das gesamte Projekt direkt im Linux-Container zu vereinen**. Die KI soll vollen, uneingeschränkten Shell-Zugriff (Root/Apt-get) auf ihr eigenes Ausführungs-System haben, ohne jemals das Windows-Host-System zu gefährden.

## Die Architektonische Vision ("The God Container")
Wir verlegen den Lebensmittelpunkt des Projekts komplett nach Linux.
1. **Host (Dein Windows-PC):** Ist nur noch der Bildschirm und das Terminal, mit dem du Befehle in den Container schickst.
2. **Der Container (Ubuntu/Debian):** Enthält alles:
   - Den virtuellen Monitor (`xvfb`)
   - Das Projekt-Repository (`Research_Automation`)
   - Den Browser (`chromium`)
   - **Neu:** Node.js und das `gemini-cli-core` npm-Paket.
3. **Der Workflow:** Anstatt das CLI auf Windows zu starten, startest du es *im* Docker-Container. Die KI (ich) wacht direkt in ihrem eigenen Gehirn (Linux) auf. Wenn ich Pakete brauche (`apt-get install`), installiere ich sie selbst. Wenn ich ein CV-Skript testen will, feure ich es direkt lokal auf dem virtuellen Monitor ab, da ich bereits in derselben Umgebung sitze.
4. **Persistenz (Volumes):** Damit Code-Änderungen und der Memory-Cache des CLIs nicht bei einem Docker-Neustart verloren gehen, mounten wir das Arbeitsverzeichnis aus Windows in den Container.

## Implementierungs-Plan

### Phase 1: Dockerfile Upgrade (The CLI Installation)
Die `Dockerfile.cvbot` wird umgebaut. Sie benötigt zusätzlich:
- Node.js (Version 20+)
- `npm install -g @google/gemini-cli-core`
- Die Einrichtung eines persistenten Workspace-Ordners (`/app/workspace`).

### Phase 2: Start-Skript für die KI
Wir erstellen ein simples Start-Skript (`start_ai_mode.sh`). 
Dieses Skript startet `xvfb` im Hintergrund und öffnet danach interaktiv das `gemini` CLI im Terminal. 
Wenn du auf Windows den Befehl `docker exec -it research_cv_agent ./start_ai_mode.sh` eingibst, hast du den KI-Chat direkt im Container.

### Phase 3: Die Sandbox-In-Sandbox (Optionaler Ausblick)
Sollte die KI im God-Container hochriskanten Code generieren (z.B. ein Skript, das wahllos Dateien löscht), kann das Gemini-CLI *selbst* innerhalb des Containers seine Sandbox-Funktion nutzen. Es würde dann isolierte Prozesse oder Micro-VMs spawnen, um den Code zu testen, bevor er auf die persistente `/app/workspace`-Festplatte geschrieben wird.

## Nächster Schritt (Für den User)
- Entscheidung: Sollen wir die `Dockerfile.cvbot` jetzt umbauen, um Node.js und das Gemini-CLI zu integrieren, sodass wir unsere nächste Entwicklungs-Session direkt im Container starten können?