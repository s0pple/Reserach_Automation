@echo off
TITLE Gemini God-Mode
REM Gehe in das Verzeichnis, in dem die Batch-Datei liegt
cd /d "%~dp0"

echo 🚀 Starte Docker Container (im Hintergrund)...
docker compose up -d

echo 🤖 Verbinde mit God-Mode CLI...
echo (Hinweis: Falls das Fenster hängen bleibt, einmal Enter drücken)
docker compose exec -it cv-agent /usr/local/bin/start_ai_mode.sh

echo.
echo 🏁 Sitzung beendet.
pause
