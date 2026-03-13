#!/bin/bash
# Starte die Docker-Umgebung und das Gemini CLI (God-Mode)

echo "🚀 Starte Research Automation Docker Umgebung..."
docker compose up -d

echo "🤖 Trete in den God-Mode Container ein..."
docker compose exec -it cv-agent /usr/local/bin/start_ai_mode.sh "$@"
