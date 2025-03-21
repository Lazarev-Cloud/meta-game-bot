#!/bin/bash
# Script to run the bot as a background service

# Ensure we're in the right directory
cd "$(dirname "$0")"

# Kill any existing bot processes
echo "Stopping any running bot instances..."
python run_bg_service.py --kill-existing

# Wait for processes to stop
sleep 2

# Start the background service with unlimited restarts
echo "Starting bot background service..."

# If virtualenv is used
if [ -d "venv" ]; then
    source venv/bin/activate
    nohup python run_bg_service.py --max-restarts=0 --restart-interval=120 > service_output.log 2>&1 &
elif [ -d "env" ]; then
    source env/bin/activate
    nohup python run_bg_service.py --max-restarts=0 --restart-interval=120 > service_output.log 2>&1 &
else
    # No virtualenv
    nohup python run_bg_service.py --max-restarts=0 --restart-interval=120 > service_output.log 2>&1 &
fi

echo "Bot service started in background with PID: $!"
echo "Use 'ps aux | grep run_bg_service' to check if it's running"
echo "Logs are being written to service.log and service_output.log" 