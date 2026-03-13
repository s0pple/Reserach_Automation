#!/bin/bash
# Check if Xvfb is already running to avoid lock errors
if ! pgrep -x "Xvfb" > /dev/null
then
    echo "🖥️ Starte virtuellen Monitor (:99)..."
    rm -f /tmp/.X99-lock
    # Fix für den Xauth-Fehler und virtuellen Monitor starten
    touch ~/.Xauthority
    Xvfb :99 -ac -screen 0 1920x1080x24 &
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

# Starte das CLI direkt aus dem Source-Code
npm start -- "$@"