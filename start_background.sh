#!/bin/bash
# Start the bot in the background after cleanup

# First run cleanup to kill any existing processes
python cleanup_and_start.py &> cleanup.log

# Wait a moment to ensure cleanup is completed
sleep 2

# Check if the bot is still running from a previous session
if pgrep -f "python run_novi_sad_game.py" > /dev/null || pgrep -f "python run_bg_service.py" > /dev/null; then
    echo "Killing remaining bot processes..."
    pkill -f "python run_novi_sad_game.py"
    pkill -f "python run_bg_service.py"
    pkill -f "python main.py"
    sleep 2
fi

# Start the background service (not the bot directly)
nohup python run_bg_service.py > service.log 2>&1 &

# Show the process ID
echo "Bot service started in the background with PID $!"
echo "Logs are being written to service.log"
echo "Use 'tail -f service.log' to monitor the logs" 