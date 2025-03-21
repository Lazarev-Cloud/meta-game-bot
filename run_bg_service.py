#!/usr/bin/env python3
# Script to run the Novi Sad Game bot as a background service
import os
import sys
import time
import subprocess
import logging
import signal
import psutil
import argparse
import tempfile
import fcntl
import errno
from datetime import datetime

# Set up logging
log_file = "service.log"
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Base lock file path
LOCK_FILE_BASE = os.path.join(tempfile.gettempdir(), 'novi_sad_bg_service')

def acquire_lock(instance_id=None):
    """
    Acquire a lock to ensure only one instance is running.
    
    Args:
        instance_id: Optional instance ID to create a unique lock file
    
    Returns:
        tuple: (lock_file_handle, lock_file_path)
    """
    try:
        # Create a unique lock file for this instance
        if instance_id:
            lock_path = f"{LOCK_FILE_BASE}_{instance_id}.lock"
        else:
            # Use environment variable if available
            env_instance_id = os.environ.get('BOT_INSTANCE_ID')
            if env_instance_id:
                lock_path = f"{LOCK_FILE_BASE}_{env_instance_id}.lock"
            else:
                # Fallback to default
                lock_path = f"{LOCK_FILE_BASE}.lock"
        
        logger.info(f"Using lock file: {lock_path}")
        
        lock_file = open(lock_path, 'w')
        fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Write PID and timestamp to lock file for better tracking
        lock_file.write(f"{os.getpid()} {datetime.now().isoformat()}")
        lock_file.flush()
        
        return lock_file, lock_path
    except IOError as e:
        if e.errno == errno.EAGAIN:
            logger.error("Another background service instance is already running. Exiting.")
            # Check for zombie lock files
            if os.path.exists(lock_path):
                try:
                    with open(lock_path, 'r') as f:
                        content = f.read().strip()
                        if content:
                            parts = content.split(' ', 1)
                            if len(parts) > 0:
                                pid = int(parts[0])
                                # Check if process is actually running
                                if not psutil.pid_exists(pid):
                                    logger.warning(f"Detected stale lock file with PID {pid} that's not running")
                                    os.remove(lock_path)
                                    logger.info(f"Removed stale lock file: {lock_path}")
                                    # Try again
                                    return acquire_lock(instance_id)
                except:
                    # If we can't read the lock file, it might be corrupted
                    logger.warning(f"Corrupted lock file: {lock_path}")
            
            sys.exit(1)
        raise

def release_lock(lock_file, lock_path=None):
    """Release the lock."""
    if lock_file:
        try:
            fcntl.flock(lock_file, fcntl.LOCK_UN)
            lock_file.close()
        except:
            pass
        
        try:
            # Remove the lock file if path is provided
            if lock_path and os.path.exists(lock_path):
                os.remove(lock_path)
                logger.info(f"Removed lock file: {lock_path}")
        except:
            pass

def signal_handler(sig, frame):
    """Handle termination signals by stopping the running bot process."""
    logger.info("Received termination signal, stopping bot...")
    find_and_kill_bot_processes()
    logger.info("Bot stopped. Exiting.")
    sys.exit(0)

def find_and_kill_bot_processes(except_instance_id=None):
    """
    Find and kill all running bot processes, except those with the specified instance ID.
    
    Args:
        except_instance_id: Instance ID to preserve (don't kill processes with this ID)
    """
    count = 0
    
    # First, try to find bot processes through psutil
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip our own process
            if proc.pid == os.getpid():
                continue
                
            # Check if it's a Python process related to our bot
            if (proc.info['name'] in ['python', 'python3', 'Python']):
                cmdline = ' '.join(proc.info['cmdline'] if proc.info['cmdline'] else [])
                
                # Skip if it has our instance ID
                if except_instance_id and (
                    f"--instance-id={except_instance_id}" in cmdline or 
                    f"BOT_INSTANCE_ID={except_instance_id}" in cmdline):
                    logger.info(f"Skipping process with our instance ID: {proc.pid}")
                    continue
                    
                if ('main.py' in cmdline or 
                    'run_novi_sad_game.py' in cmdline or 
                    'telegram' in cmdline or
                    'getUpdates' in cmdline) and proc.pid != os.getpid():
                    logger.info(f"Terminating bot process: PID {proc.pid}, cmdline: {cmdline}")
                    try:
                        # First try to terminate gracefully
                        proc.terminate()
                        count += 1
                        time.sleep(1.5)  # Longer pause to allow for graceful termination
                        
                        # If still running, use kill
                        if psutil.pid_exists(proc.pid):
                            logger.info(f"Process {proc.pid} still alive, using SIGKILL")
                            proc.kill()
                            time.sleep(1.5)  # Wait to ensure termination
                            
                            # Final check
                            if psutil.pid_exists(proc.pid):
                                logger.warning(f"Process {proc.pid} could not be terminated!")
                    except Exception as e:
                        logger.error(f"Error killing process {proc.pid}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.warning(f"Error accessing process: {e}")
    
    # Additional approach: Use direct shell commands for better reliability
    try:
        cmd = "ps aux | grep -E 'python.*main.py|python.*run_novi_sad_game.py|.*getUpdates|telegram.org' | grep -v grep || true"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.stdout.strip():
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    cmdline = ' '.join(parts[10:]) if len(parts) > 10 else ''
                    
                    # Skip if it has our instance ID
                    if except_instance_id and (
                        f"--instance-id={except_instance_id}" in cmdline or 
                        f"BOT_INSTANCE_ID={except_instance_id}" in cmdline):
                        continue
                    
                    # Skip our own process
                    if int(pid) == os.getpid():
                        continue
                        
                    logger.info(f"Killing bot process from shell: PID {pid}")
                    try:
                        # Try SIGTERM first
                        subprocess.run(["kill", pid], stderr=subprocess.DEVNULL)
                        time.sleep(1)
                        
                        # If still running, use SIGKILL
                        if psutil.pid_exists(int(pid)):
                            subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL)
                            count += 1
                    except Exception as e:
                        logger.error(f"Error killing process {pid}: {e}")
    except Exception as e:
        logger.error(f"Error using shell command to find and kill processes: {e}")
    
    # Clear any Telegram webhook connections
    try:
        token = os.environ.get('TELEGRAM_BOT_TOKEN')
        if token:
            import requests
            logger.info("Resetting Telegram webhook...")
            response = requests.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook",
                params={"drop_pending_updates": True}
            )
            logger.info(f"Webhook reset response: {response.status_code}")
            time.sleep(1)  # Give the API a moment
    except Exception as e:
        logger.error(f"Error resetting webhook: {e}")
    
    # Wait a moment to ensure all processes have terminated
    if count > 0:
        logger.info(f"Killed {count} bot-related processes. Waiting for full termination...")
        time.sleep(3)
    else:
        logger.info("No existing bot processes found to kill")
    
    # Final verification
    try:
        cmd = "ps aux | grep -E 'python.*main.py|python.*run_novi_sad_game.py|.*getUpdates|telegram.org' | grep -v grep || true"
        result = subprocess.run(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.stdout.strip():
            logger.warning("Some bot processes are still running after cleanup:")
            for line in result.stdout.splitlines():
                logger.warning(line)
    except:
        pass
    
    return count

def stop_existing_bots():
    """Stop any existing bot processes."""
    try:
        # Find and kill any existing python processes running main.py
        for proc in psutil.process_iter():
            try:
                # Check if the process name matches our bot
                if proc.name() == "python" and "main.py" in ' '.join(proc.cmdline()):
                    # Don't kill our own process
                    if proc.pid != os.getpid():
                        logging.info(f"Stopping existing bot process: {proc.pid}")
                        proc.terminate()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
        
        # Give processes time to terminate
        time.sleep(2)
        
        # Force kill any that didn't terminate
        for proc in psutil.process_iter():
            try:
                if proc.name() == "python" and "main.py" in ' '.join(proc.cmdline()):
                    if proc.pid != os.getpid():
                        logging.warning(f"Force killing bot process: {proc.pid}")
                        proc.kill()
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                pass
    except Exception as e:
        logging.error(f"Error stopping existing bots: {e}")

def run_service():
    """Run the background service."""
    try:
        # Stop any existing bot processes
        stop_existing_bots()
        
        # Start the bot with a unique instance ID
        instance_id = str(int(time.time()))
        cmd = f"python main.py --instance-id={instance_id}"
        
        logging.info(f"Starting bot with command: {cmd}")
        
        with open("bot_output.log", "a") as output_log:
            process = subprocess.Popen(
                cmd, 
                shell=True,
                stdout=output_log,
                stderr=output_log
            )
            
        # Wait for process to start
        time.sleep(2)
        
        if process.poll() is not None:
            logging.error(f"Bot process failed to start. Exit code: {process.returncode}")
            return False
        
        logging.info(f"Bot process started with PID: {process.pid}")
        return True
    except Exception as e:
        logging.error(f"Error running service: {e}")
        return False

def run_bot_with_restart(max_restart_count=None, restart_interval=60, instance_id=None):
    """
    Run the bot with automatic restarts
    
    Args:
        max_restart_count: Maximum number of automatic restarts (None for unlimited)
        restart_interval: Time to wait between restarts (in seconds)
        instance_id: Optional instance ID to identify this service
    """
    restart_count = 0
    lock_file = None
    lock_path = None
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    try:
        # Acquire lock to ensure only one instance is running
        lock_file, lock_path = acquire_lock(instance_id)
        
        # Set instance ID environment variable if provided
        if instance_id:
            os.environ['BOT_INSTANCE_ID'] = instance_id
            
        # First stop any existing bot processes
        stop_existing_bots()
        logger.info(f"Starting bot with restart capability. Max restarts: {max_restart_count if max_restart_count is not None else 'unlimited'}, Interval: {restart_interval}s")
        
        while True:
            # Check if we've hit the maximum restart count
            if max_restart_count is not None and restart_count >= max_restart_count:
                logger.warning(f"Reached maximum restart count of {max_restart_count}. Exiting.")
                break
                
            start_time = time.time()
            logger.info(f"Starting bot (restart #{restart_count if restart_count > 0 else 'initial run'})")
            
            # Run the service
            success = run_service()
            
            if not success:
                logger.error("Bot failed to start properly")
                time.sleep(10)  # Wait longer before retry on start failure
                restart_count += 1
                continue
                
            # If we get here, the bot has stopped
            elapsed_time = time.time() - start_time
            
            if elapsed_time < 60:
                logger.warning(f"Bot exited too quickly after {elapsed_time:.1f} seconds! Increasing wait time before restart.")
                time.sleep(min(restart_interval * 2, 300))  # Up to 5 minutes
            else:
                logger.info(f"Bot ran for {elapsed_time:.1f} seconds. Restarting after {restart_interval} seconds...")
                time.sleep(restart_interval)
                
            restart_count += 1
    except KeyboardInterrupt:
        logger.info("Caught keyboard interrupt. Shutting down...")
    except Exception as e:
        logger.error(f"Error in main loop: {e}")
    finally:
        # Make sure to kill any bot processes when we exit
        find_and_kill_bot_processes()
        
        # Release lock
        release_lock(lock_file, lock_path)
        
        logger.info("Background service stopped")

def main():
    parser = argparse.ArgumentParser(description="Run the Novi Sad Game bot as a background service")
    parser.add_argument("--max-restarts", type=int, default=None, 
                        help="Maximum number of restarts (default: unlimited)")
    parser.add_argument("--restart-interval", type=int, default=60,
                        help="Seconds to wait between restarts (default: 60)")
    parser.add_argument("--instance-id", type=str, default=None,
                        help="Unique instance ID for this service (default: none)")
    parser.add_argument("--kill-existing", action="store_true",
                        help="Kill existing bot processes and exit")
                        
    args = parser.parse_args()
    
    # If just killing existing processes
    if args.kill_existing:
        count = find_and_kill_bot_processes()
        sys.exit(0)
        
    # Otherwise run the service
    run_bot_with_restart(
        max_restart_count=args.max_restarts,
        restart_interval=args.restart_interval,
        instance_id=args.instance_id
    )

if __name__ == "__main__":
    main() 