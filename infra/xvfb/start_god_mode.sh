#!/bin/bash
# Startet das Gemini CLI im God-Container (Linux/WSL-Version)

# Projekt-Root sicherstellen
PROJECT_ROOT="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"
DOCKER_CONFIG="$PROJECT_ROOT/infra/docker/docker-compose.yml"

echo "🚀 Starte Research Automation God-Container..."

# Prüfe, ob Docker läuft
if ! docker info > /dev/null 2>&1; then
    echo "❌ Fehler: Docker läuft nicht oder du hast keine Berechtigungen."
    exit 1
fi

# Container starten
docker compose --project-directory "$PROJECT_ROOT" -f "$DOCKER_CONFIG" up -d

echo "🤖 Betrete den God-Mode..."
# In den Container wechseln und das interne Start-Skript ausführen
docker compose --project-directory "$PROJECT_ROOT" -f "$DOCKER_CONFIG" exec -it cv-agent /bin/bash /app/infra/xvfb/start_ai_mode.sh "$@"
