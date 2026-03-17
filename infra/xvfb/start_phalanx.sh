#!/bin/bash
# Phalanx 2.0 Watchdog & Daemon
# Sorgt dafür, dass der Bot 24/7 läuft, auch nach Abstürzen.

LOG_FILE="/tmp/phalanx_daemon.log"
PROJECT_DIR="/app"

echo "$(date): Phalanx Daemon gestartet." >> $LOG_FILE

while true; do
    # Prüfen, ob der Bot-Prozess läuft (Telegram Polling)
    PID=$(pgrep -f "python3 main.py --mode telegram")
    
    if [ -z "$PID" ]; then
        echo "$(date): Bot nicht gefunden! Starte Phalanx 2.0 neu..." >> $LOG_FILE
        cd $PROJECT_DIR
        # Starte den Bot und leite Logs um
        python3 main.py --mode telegram >> /tmp/bot_live.log 2>&1 &
        echo "$(date): Bot mit PID $! gestartet." >> $LOG_FILE
    fi
    
    # Warte 30 Sekunden vor dem nächsten Check
    sleep 30
done
