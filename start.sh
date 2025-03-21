#!/bin/bash
# Comprehensive startup script for the Meta Game Bot
# This script handles:
# 1. Killing all existing bot processes
# 2. Cleaning up lock files
# 3. Rotating logs
# 4. Starting a fresh bot instance

# Print header
echo "===================================================="
echo "        Meta Game Bot - Startup Script"
echo "===================================================="
echo ""

# Check if TOKEN environment variable is set
if [ -z "${TELEGRAM_BOT_TOKEN}" ]; then
    echo "❌ Error: TELEGRAM_BOT_TOKEN environment variable is not set!"
    echo "Please set it with your Telegram Bot API token to run the bot."
    echo "Example: export TELEGRAM_BOT_TOKEN=your_token_here"
    exit 1
fi

# Kill any existing bot processes
echo "Stopping any running bot instances..."
pkill -f "python main.py" || true

# Wait a moment for processes to stop
sleep 2

# Start the bot
echo "Starting the bot..."
source .venv/bin/activate && python main.py

# Kill any running bot or Telegram processes
kill_bot_processes() {
    echo "🧹 Cleaning up existing processes..."
    echo "🔪 Forcefully killing any existing bot processes..."
    
    # Find and kill all Python processes that might be related to the bot
    for pid in $(ps aux | grep -E "python.*main.py|python.*run_bg_service.py|python.*novi_sad|.*getUpdates" | grep -v grep | awk '{print $2}'); do
        echo "Killing process $pid"
        kill -9 $pid 2>/dev/null || true
    done
    
    # Wait to ensure they're actually gone
    sleep 2
    
    # Check if any processes are still running
    if ps aux | grep -E "python.*main.py|python.*run_bg_service.py|python.*novi_sad|.*getUpdates" | grep -v grep > /dev/null; then
        echo "⚠️ Warning: Some bot processes are still running. Trying more aggressive cleanup..."
        # Try a more aggressive approach
        for pid in $(ps aux | grep -E "python.*main.py|python.*run_bg_service.py|python.*novi_sad|.*getUpdates" | grep -v grep | awk '{print $2}'); do
            echo "Force killing process $pid"
            kill -9 $pid 2>/dev/null || true
        done
        sleep 2
    fi
    
    # Clean up lock files in various temp directories
    echo "🧹 Cleaning lock files from all possible locations..."
    find /var/folders -name "novi_sad_*.lock" -delete 2>/dev/null || true
    find /tmp -name "novi_sad_*.lock" -delete 2>/dev/null || true
    find ~/Library/Caches -name "novi_sad_*.lock" -delete 2>/dev/null || true
    find /private/tmp -name "novi_sad_*.lock" -delete 2>/dev/null || true
    find /private/var/folders -name "novi_sad_*.lock" -delete 2>/dev/null || true
    
    # Remove standard lock files
    rm -f /tmp/novi_sad_bot.lock /tmp/novi_sad_bg_service.lock /tmp/novi_sad_game.lock 2>/dev/null || true
    
    # Reset Telegram webhook to clear any lingering connections
    if [ -n "$TELEGRAM_BOT_TOKEN" ]; then
        echo "🔄 Resetting Telegram webhook..."
        curl -s "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/deleteWebhook?drop_pending_updates=true" > /dev/null
        # Wait to ensure the webhook is cleared
        sleep 2
    else
        # Try to extract from .env if available
        if [ -f .env ]; then
            TOKEN=$(grep TELEGRAM_BOT_TOKEN .env | cut -d'=' -f2 | tr -d "'\"")
            if [ -n "$TOKEN" ]; then
                echo "🔄 Resetting Telegram webhook..."
                curl -s "https://api.telegram.org/bot$TOKEN/deleteWebhook?drop_pending_updates=true" > /dev/null
                # Wait to ensure the webhook is cleared
                sleep 2
            fi
        fi
    fi
    
    # Verify all processes are gone
    echo "🔍 Verifying all bot processes are terminated..."
    if ps aux | grep -E "python.*main.py|python.*run_bg_service.py|python.*novi_sad|.*getUpdates" | grep -v grep > /dev/null; then
        echo "⚠️ Warning: Some bot processes are still detected. Attempting more aggressive cleanup..."
        # Try more aggressive process killing with killall
        killall -9 Python 2>/dev/null || true
        sleep 2
    fi
    
    echo "✅ Cleanup complete"
}

# At the beginning of the script execution
echo "🧹 Running comprehensive cleanup..."
# Make the cleanup script executable
chmod +x cleanup.py
# Run the Python cleanup script
python cleanup.py

# Wait to ensure processes are terminated
echo "⏳ Waiting for processes to terminate..."
sleep 5

# Perform additional cleanup just to be sure
kill_bot_processes

# Clean up lock files - additional pass
echo "🧹 Cleaning up lock files..."
find /var -name "*novi_sad*" -type f -delete 2>/dev/null || true
rm -f /tmp/novi_sad_bot.lock /tmp/novi_sad_bg_service.lock /tmp/novi_sad_game.lock 2>/dev/null

# Rotate log files
echo "📝 Rotating log files..."
for logfile in bot.log service.log bot_output.log cleanup.log nohup.out; do
    if [ -f "$logfile" ]; then
        mv "$logfile" "${logfile}.$(date +%Y%m%d-%H%M%S).old"
    fi
done

# Check if we should skip database setup
SKIP_SETUP=0
while [[ $# -gt 0 ]]; do
  case $1 in
    --skip-setup)
      SKIP_SETUP=1
      shift
      ;;
    *)
      shift
      ;;
  esac
done

# Check for virtual environment
if [ -d ".venv" ]; then
    echo "🔄 Activating virtual environment..."
    source .venv/bin/activate
fi

# Generate a unique instance ID
INSTANCE_ID=$(date +%s)
export BOT_INSTANCE_ID=$INSTANCE_ID

# Start the bot
echo "🚀 Starting the bot with instance ID: $INSTANCE_ID..."
if [ $SKIP_SETUP -eq 1 ]; then
    echo "🔄 Skipping database setup..."
    nohup python run_bg_service.py --max-restarts=5 --instance-id=$INSTANCE_ID > service.log 2>&1 &
else
    echo "🔄 Running with database setup..."
    # First initialize the database
    python init_db.py
    # Then start the background service
    nohup python run_bg_service.py --max-restarts=5 --instance-id=$INSTANCE_ID > service.log 2>&1 &
fi

# Get the process ID
BOT_PID=$!
echo "✅ Bot service started with PID: $BOT_PID and instance ID: $INSTANCE_ID"
echo "📝 Logs are being written to service.log"
echo "💡 Use 'tail -f service.log' to monitor the logs" 