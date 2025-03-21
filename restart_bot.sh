#!/bin/bash
# Restart the Novi Sad Game Bot
# This script safely stops any running bot instances and starts a new one

echo "====================="
echo "Restarting Bot Service"
echo "====================="

# First reset the Telegram webhook
echo "Resetting Telegram webhook..."
python stop-webhook.py --force || echo "Warning: Failed to reset webhook"
sleep 2

# Kill any existing bot processes - checking by command patterns
echo "Killing existing bot processes..."
for pid in $(ps aux | grep -E "python.*run_novi_sad_game.py|python.*run_bg_service.py|python.*main.py|telegram.org|getUpdates" | grep -v grep | awk '{print $2}'); do
    echo "Killing process $pid"
    kill -9 $pid 2>/dev/null || true
done

# Wait to ensure processes are terminated
echo "Waiting for processes to terminate..."
sleep 3

# Check if any bot processes are still running
if ps aux | grep -E "python.*run_novi_sad_game.py|python.*run_bg_service.py|python.*main.py|telegram.org|getUpdates" | grep -v grep > /dev/null; then
    echo "Warning: Some bot processes are still running. Forcing termination..."
    for pid in $(ps aux | grep -E "python.*run_novi_sad_game.py|python.*run_bg_service.py|python.*main.py|telegram.org|getUpdates" | grep -v grep | awk '{print $2}'); do
        echo "Force killing process $pid"
        kill -9 $pid 2>/dev/null || true
    done
    sleep 3
fi

# Run the comprehensive cleanup script
echo "Running comprehensive cleanup..."
python cleanup.py

# Clean up lock files
echo "Cleaning up lock files..."
rm -f /tmp/novi_sad_bot.lock /tmp/novi_sad_bg_service.lock /tmp/novi_sad_game*.lock 2>/dev/null
find /var/folders -name "novi_sad_*.lock" -delete 2>/dev/null || true
find /tmp -name "novi_sad_*.lock" -delete 2>/dev/null || true

# Remove old log files
echo "Cleaning up old log files..."
current_time=$(date +%Y%m%d-%H%M%S)
for logfile in bot.log service.log bot_output.log cleanup.log; do
    if [ -f "$logfile" ]; then
        mv "$logfile" "${logfile}.${current_time}.old" 2>/dev/null
    fi
done

# Generate a unique instance ID
INSTANCE_ID=$(date +%s)
export BOT_INSTANCE_ID=$INSTANCE_ID

# Start the bot in the background using the background service
echo "Starting bot service with instance ID: $INSTANCE_ID..."
nohup python run_bg_service.py --max-restarts=5 --instance-id=$INSTANCE_ID > service.log 2>&1 &

# Show the process ID
BOT_PID=$!
echo "Bot service started with PID: $BOT_PID and instance ID: $INSTANCE_ID"
echo "Logs are being written to service.log"
echo "Use 'tail -f service.log' to monitor the logs"

echo ""
echo "✓ Restart completed successfully" 