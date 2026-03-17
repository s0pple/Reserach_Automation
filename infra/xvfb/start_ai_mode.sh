#!/bin/bash
# Check if Xvfb is already running to avoid lock errors
if ! pgrep -x ""Xvfb"" > /dev/null
then
    echo "🖥️ Starte virtuellen Monitor (:99)..."
    rm -f /tmp/.X99-lock
    # Fix für den Xauth-Fehler und virtuellen Monitor starten
    touch ~/.Xauthority
    Xvfb :99 -ac -screen 0 1920x1080x24 &
    sleep 2
    # Start Window Manager and set background to avoid black screen
    nohup fluxbox -display :99 > /dev/null 2>&1 &
    sleep 1
    nohup xsetroot -display :99 -solid "#2E3440" > /dev/null 2>&1 &
else
    echo "🖥️ Virtueller Monitor (:99) läuft bereits."
fi

export DISPLAY=:99

# Zwinge Linux in den 256-Farben-Modus (behebt das Color-Bugging im Docker-Terminal)
export TERM=xterm-256color
export COLORTERM=truecolor
export FORCE_COLOR=1

echo "🤖 Starte God-Container AI (Custom Gemini CLI)..."

# Gehe in das gespiegelte Verzeichnis deiner Custom-CLI
cd /gemini-cli-custom

# Mache npm install / build NUR beim allerersten Mal, um extreme Boot-Zeiten zu vermeiden
if [ ! -d "node_modules" ] || [ ! -d "packages/cli/dist" ]; then
    echo "📦 Installiere und Baue Node Modules für Custom CLI (Einmalig)..."
    npm install
    npm run build
fi

# Starte das CLI über das neue Bundle aus dem Arbeitsverzeichnis heraus
cd /app

# 1. Klicke in den Terminal und frage nach Sandbox
echo ""
echo "🛡️ Sandbox-Modus aktivieren? (Wir sind bereits in Docker, dies ändert nur das UI-Verhalten)"
read -p "   [y] Ja | [n] Nein (Standard): " use_sandbox

if [[ "$use_sandbox" == "y" ]] || [[ "$use_sandbox" == "Y" ]]; then
    export SANDBOX="docker"
    echo "✅ Sandbox-Umgebung (Docker) wird der CLI signalisiert."
else
    echo "❌ Keine Sandbox signalisiert."
fi

echo ""
# Starte das CLI 
node /gemini-cli-custom/bundle/gemini.js "$@"