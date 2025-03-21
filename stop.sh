#!/bin/bash
# Script to safely stop all running bot instances

echo "===================================================="
echo "        Meta Game Bot - Stop Script"
echo "===================================================="
echo ""

echo "🛑 Stopping all bot processes..."

# Send SIGTERM to allow for graceful shutdown
pkill -f "python.*run_novi_sad_game.py"
pkill -f "python.*run_bg_service.py"
pkill -f "python.*main.py"
pkill -f ".*getUpdates"
pkill -f ".*telegram.org"

# Wait a moment
echo "⏳ Waiting for processes to terminate..."
sleep 3

# Now run the comprehensive cleanup script
echo "🧹 Running comprehensive cleanup..."
# Make the cleanup script executable
chmod +x cleanup.py
# Run the Python cleanup script
python cleanup.py

# Additional manual cleanup - just to be absolutely sure
echo "🧹 Final cleanup check..."
if pgrep -f "python.*main.py" > /dev/null || pgrep -f ".*getUpdates" > /dev/null; then
    echo "⚠️ Still detecting processes. Using killall as last resort..."
    killall -9 Python 2>/dev/null || true
    sleep 2
fi

echo "✅ All bot processes have been stopped" 