#!/bin/bash
# Check if Xvfb is already running to avoid lock errors
if ! pgrep -x "Xvfb" > /dev/null
then
    echo "🖥️ Starte virtuellen Monitor (:99)..."
    rm -f /tmp/.X99-lock
    Xvfb :99 -screen 0 1920x1080x24 &
else
    echo "🖥️ Virtueller Monitor (:99) läuft bereits."
fi

export DISPLAY=:99

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