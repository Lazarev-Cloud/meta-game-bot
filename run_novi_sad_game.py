#!/usr/bin/env python3
import os
import sys
import subprocess
import logging
import time
import signal
import psutil
import argparse
import re
import tempfile
import fcntl
import errno

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

# Lock file to prevent multiple instances
LOCK_FILE = os.path.join(tempfile.gettempdir(), 'novi_sad_game.lock')

def acquire_lock():
    """Acquire a lock to ensure only one instance is running."""
    try:
        # Check for instance ID
        instance_id = None
        for arg in sys.argv:
            match = re.match(r'--instance-id=(\d+)', arg)
            if match:
                instance_id = match.group(1)
                break
        
        # Use environment if not found in args
        if not instance_id:
            instance_id = os.environ.get('BOT_INSTANCE_ID')
        
        # Create instance-specific lock file if we have an ID
        lock_path = LOCK_FILE
        if instance_id:
            lock_path = os.path.join(tempfile.gettempdir(), f'novi_sad_game_{instance_id}.lock')
        
        lock_file = open(lock_path, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        # Write PID to file for tracking
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        # Return both the file handle and path
        return lock_file, lock_path
    except IOError as e:
        if e.errno == errno.EAGAIN:
            logger.error("Another game instance is already running. Exiting.")
            sys.exit(1)
        raise

def release_lock(lock_file, lock_path=None):
    """Release the lock."""
    if lock_file:
        fcntl.flock(lock_file, fcntl.LOCK_UN)
        lock_file.close()
        try:
            # Remove the lock file if path provided
            if lock_path and os.path.exists(lock_path):
                os.remove(lock_path)
            # For backward compatibility
            elif os.path.exists(LOCK_FILE):
                os.remove(LOCK_FILE)
        except:
            pass

def kill_existing_bot_instances():
    """Kill any existing bot processes that might cause conflicts."""
    current_pid = os.getpid()
    killed_count = 0
    
    # Get our instance ID if specified
    instance_id = None
    for arg in sys.argv:
        match = re.match(r'--instance-id=(\d+)', arg)
        if match:
            instance_id = match.group(1)
            break
    
    # Also check environment variable
    if not instance_id:
        instance_id = os.environ.get('BOT_INSTANCE_ID')
    
    logger.info(f"Running with instance ID: {instance_id}")
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip our own process
            if proc.pid == current_pid:
                continue
                
            # Check if it's a Python process and related to our bot
            if (proc.info['name'] in ['python', 'python3']):
                cmdline = ' '.join(proc.info['cmdline'] if proc.info['cmdline'] else [])
                
                # Skip processes with the same instance ID
                if instance_id and f"--instance-id={instance_id}" in cmdline:
                    continue
                    
                if 'main.py' in cmdline or 'telegram' in cmdline or 'getUpdates' in cmdline:
                    logger.info(f"Terminating existing bot process: PID {proc.pid}, cmdline: {cmdline}")
                    try:
                        os.kill(proc.pid, signal.SIGTERM)
                        killed_count += 1
                        time.sleep(1.5)  # Give it a moment to terminate
                        
                        # If still running, force kill
                        if psutil.pid_exists(proc.pid):
                            logger.info(f"Process {proc.pid} still alive, using SIGKILL")
                            os.kill(proc.pid, signal.SIGKILL)
                            time.sleep(1)  # Wait to ensure termination
                    except OSError as e:
                        logger.error(f"Error killing process {proc.pid}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.warning(f"Error accessing process: {e}")
    
    if killed_count > 0:
        logger.info(f"Killed {killed_count} existing bot processes")
        # Wait a bit to ensure system resources are freed
        time.sleep(2)
    
    return killed_count

def setup_novi_sad():
    """Set up the Novi Sad game environment."""
    try:
        # First, initialize the database
        print("Initializing database...")
        db_init_result = subprocess.run(
            [sys.executable, "init_db.py"],
            check=True,
            capture_output=True,
            text=True
        )
        print(db_init_result.stdout)
        
        # Ensure the districts are properly set up
        print("Setting up Novi Sad districts...")
        districts_result = subprocess.run(
            [sys.executable, "create_districts.py"],
            check=True,
            capture_output=True,
            text=True
        )
        print(districts_result.stdout)
        
        # Set up politicians
        print("Setting up Novi Sad politicians...")
        politicians_result = subprocess.run(
            [sys.executable, "create_politicians.py"],
            check=True,
            capture_output=True,
            text=True
        )
        print(politicians_result.stdout)
        
        # Verify setup
        print("Verifying Novi Sad setup...")
        verify_result = subprocess.run(
            [sys.executable, "check_novi_sad_setup.py"],
            check=True,
            capture_output=True,
            text=True
        )
        print(verify_result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error during setup: {e}")
        print(f"Output: {e.stdout}\nError: {e.stderr}")
        return False

def run_game():
    """Run the game with Novi Sad settings."""
    try:
        # Check if TOKEN environment variable is set
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if not token:
            print("⚠️ TELEGRAM_BOT_TOKEN environment variable is not set!")
            print("You need to set it with your Telegram Bot API token to run the bot.")
            print("Example: export TELEGRAM_BOT_TOKEN=your_token_here")
            return False
        
        # Kill any existing bot instances to prevent conflicts
        kill_existing_bot_instances()
        
        # Start the bot with automatic restart on failure
        max_retries = 3
        retry_count = 0
        
        # Get instance ID if specified
        instance_id = None
        for arg in sys.argv:
            match = re.match(r'--instance-id=(\d+)', arg)
            if match:
                instance_id = match.group(1)
                break
        
        # Also check environment variable
        if not instance_id:
            instance_id = os.environ.get('BOT_INSTANCE_ID')
        
        while retry_count < max_retries:
            try:
                print(f"🚀 Starting Novi Sad Game Bot (attempt {retry_count + 1}/{max_retries})...")
                
                # Prepare command with instance ID if available
                command = [sys.executable, "main.py"]
                if instance_id:
                    command.append(f"--instance-id={instance_id}")
                
                bot_process = subprocess.run(
                    command,
                    check=True
                )
                # If we get here, the bot exited cleanly
                return True
            except subprocess.CalledProcessError as e:
                retry_count += 1
                print(f"Bot process failed with error code {e.returncode}")
                if retry_count < max_retries:
                    print(f"Retrying in 5 seconds... (attempt {retry_count + 1}/{max_retries})")
                    time.sleep(5)
                else:
                    print("Maximum retry attempts reached.")
                    return False
        
        return False
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
        return True
    except Exception as e:
        print(f"Unexpected error running the bot: {e}")
        return False

if __name__ == "__main__":
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Run the Novi Sad Game Bot")
    parser.add_argument("--skip-setup", action="store_true", help="Skip database setup")
    parser.add_argument("--instance-id", type=str, help="Unique instance ID to avoid conflicts")
    
    args, unknown = parser.parse_known_args()
    
    # Set instance ID in environment if provided
    if args.instance_id:
        os.environ['BOT_INSTANCE_ID'] = args.instance_id
    
    # Acquire lock to prevent multiple instances
    lock_file, lock_path = acquire_lock()
    
    try:
        print("=====================================")
        print("🎮 Novi Sad Game - Yugoslavia 1990s 🎮")
        print("=====================================")
        
        # Check if we should skip setup
        skip_setup = args.skip_setup
        
        if not skip_setup:
            print("\n📋 Running Novi Sad setup...")
            if not setup_novi_sad():
                print("\n❌ Setup failed! Please check the errors above.")
                sys.exit(1)
        else:
            print("\n🔄 Skipping setup (--skip-setup flag detected)")
        
        print("\n🚀 Starting the game...")
        success = run_game()
        
        print("\n✅ Game session ended" if success else "\n❌ Game session failed")
    finally:
        # Release lock
        release_lock(lock_file, lock_path) 