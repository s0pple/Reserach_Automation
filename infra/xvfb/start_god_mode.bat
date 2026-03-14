@echo off
REM Gehe in das Root-Verzeichnis des Projekts
cd /d "%~dp0\..\.."

echo 🚀 Starte Docker Container (im Hintergrund)...
docker compose --project-directory . -f infra/docker/docker-compose.yml up -d

echo 🤖 Verbinde mit God-Mode CLI...
echo (Hinweis: Falls das Fenster hängen bleibt, einmal Enter drücken)
docker compose --project-directory . -f infra/docker/docker-compose.yml exec -it cv-agent /bin/bash /app/infra/xvfb/start_ai_mode.sh
