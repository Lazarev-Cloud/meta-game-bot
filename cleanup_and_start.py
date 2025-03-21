#!/usr/bin/env python3
"""
Script to thoroughly clean up any existing bot processes and start the bot.
This helps resolve conflicts with multiple bot instances.
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import logging
import tempfile
import fcntl
import errno
import re

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("cleanup.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Lock file to prevent multiple instances
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'novi_sad_bot.lock')

def acquire_lock():
    """Acquire a lock to ensure only one instance is running."""
    try:
        lock_file = open(LOCK_FILE, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Keep the file handle open to maintain the lock
        return lock_file
    except IOError as e:
        if e.errno == errno.EAGAIN:
            logger.error("Another instance is already running. Exiting.")
            sys.exit(1)
        raise

def release_lock(lock_file):
    """Release the lock."""
    if lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        try:
            os.remove(LOCK_FILE)
        except:
            pass

def kill_bot_processes():
    """Kill any running bot processes."""
    try:
        # Find and kill all Python processes running main.py
        main_pattern = r'python.*main\.py'
        main_processes = find_processes_by_pattern(main_pattern)
        
        # Find and kill all Python processes running run_bg_service.py
        bg_pattern = r'python.*run_bg_service\.py'
        bg_processes = find_processes_by_pattern(bg_pattern)
        
        # Find any Python processes with "novi_sad" in their command line
        novi_sad_pattern = r'python.*novi_sad'
        novi_sad_processes = find_processes_by_pattern(novi_sad_pattern)
        
        all_processes = main_processes + bg_processes + novi_sad_processes
        
        # Deduplicate processes
        pids_seen = set()
        unique_processes = []
        for proc in all_processes:
            if proc.pid not in pids_seen:
                pids_seen.add(proc.pid)
                unique_processes.append(proc)
        
        for proc in unique_processes:
            try:
                # Try to kill nicely first
                proc.terminate()
                logger.info(f"Terminated process {proc.pid}: {proc.cmdline()}")
            except psutil.NoSuchProcess:
                pass
        
        # Wait for processes to terminate
        psutil.wait_procs(unique_processes, timeout=2)
        
        # Force kill any remaining processes
        for proc in unique_processes:
            try:
                if proc.is_running():
                    proc.kill()
                    logger.info(f"Force killed process {proc.pid}: {proc.cmdline()}")
            except psutil.NoSuchProcess:
                pass
        
        # Also try OS-specific commands for thoroughness
        try:
            # For Unix-like systems
            os.system("pkill -f 'python.*main.py'")
            os.system("pkill -f 'python.*run_bg_service.py'")
            os.system("pkill -f 'python.*novi_sad'")
        except:
            pass
            
        # Remove all lock files
        lock_files = [
            # Temp directory lock files
            os.path.join(tempfile.gettempdir(), 'novi_sad_game.lock'),
            os.path.join(tempfile.gettempdir(), 'novi_sad_bg_service.lock'),
            os.path.join(tempfile.gettempdir(), 'novi_sad_bot.lock'),
            # Any other lock files you might have
        ]
        
        for lock_file in lock_files:
            try:
                if os.path.exists(lock_file):
                    os.remove(lock_file)
                    logger.info(f"Removed lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Failed to remove lock file {lock_file}: {e}")
                
        return len(unique_processes)
    except Exception as e:
        logger.error(f"Error killing bot processes: {e}")
        return 0

def check_environment():
    """Check if environment is properly set up."""
    # Check for TOKEN
    token = os.environ.get('TELEGRAM_BOT_TOKEN')
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        logger.error("Set it with: export TELEGRAM_BOT_TOKEN=your_token_here")
        return False
    
    # Check for database file
    if not os.path.exists('novi_sad_game.db'):
        logger.error("novi_sad_game.db not found. Database needs to be initialized.")
        return False
    
    return True

def start_bot():
    """Start the bot with the skip-setup flag."""
    logger.info("Starting the bot...")
    
    try:
        # Start without the background service wrapper for cleaner logs
        subprocess.run(
            [sys.executable, "run_novi_sad_game.py", "--skip-setup"],
            check=True
        )
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Bot process failed with error code {e.returncode}")
        return False
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
        return True

def find_processes_by_pattern(pattern):
    """Find processes matching a given pattern."""
    processes = []
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if re.match(pattern, ' '.join(proc.info['cmdline'] if proc.info['cmdline'] else [])):
            processes.append(proc)
    return processes

if __name__ == "__main__":
    # Acquire lock to prevent multiple instances
    lock_file = acquire_lock()
    
    try:
        print("=" * 50)
        print("🧹 Clean-up and Start Bot Script")
        print("=" * 50)
        
        # Step 1: Kill any existing bot processes
        print("\n1. Killing any existing bot processes...")
        killed = kill_bot_processes()
        print(f"   Killed {killed} bot-related processes")
        
        # Short pause to ensure everything is terminated
        time.sleep(2)
        
        # Step 2: Check environment
        print("\n2. Checking environment...")
        if not check_environment():
            print("   ❌ Environment check failed. Please fix the issues above.")
            sys.exit(1)
        print("   ✅ Environment check passed")
        
        # Step 3: Start the bot
        print("\n3. Starting the bot...")
        success = start_bot()
        
        if success:
            print("\n✅ Bot session ended normally")
            sys.exit(0)
        else:
            print("\n❌ Bot session failed")
            sys.exit(1)
    finally:
        # Release lock when done
        release_lock(lock_file) 