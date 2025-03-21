#!/usr/bin/env python3
"""
Reset the database and start the Novi Sad Game Bot
This script will:
1. Kill any running bot processes
2. Delete the existing database
3. Recreate the database and set up districts and politicians
4. Start the bot in the background
"""

import os
import sys
import time
import signal
import subprocess
import psutil
import logging
import sqlite3

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler("reset.log"),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

def kill_all_bot_processes():
    """Find and kill all running bot processes."""
    killed_count = 0
    
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            # Skip our own process
            if proc.pid == os.getpid():
                continue
                
            if proc.info['name'] in ['python', 'python3']:
                cmdline = ' '.join(proc.info['cmdline'] if proc.info['cmdline'] else [])
                
                # Keywords that indicate it's a bot-related process
                keywords = ['main.py', 'telegram', 'run_novi_sad_game.py', 'run_bg_service.py']
                
                if any(keyword in cmdline for keyword in keywords):
                    logger.info(f"Found bot process: PID {proc.pid}, cmdline: {cmdline}")
                    
                    # Try to kill with SIGTERM first
                    try:
                        logger.info(f"Sending SIGTERM to PID {proc.pid}")
                        os.kill(proc.pid, signal.SIGTERM)
                        time.sleep(1.0)  # Longer pause to allow for graceful termination
                        
                        # If still running, use SIGKILL
                        if psutil.pid_exists(proc.pid):
                            logger.info(f"Process {proc.pid} still alive, sending SIGKILL")
                            os.kill(proc.pid, signal.SIGKILL)
                            time.sleep(1.0)  # Give it time to fully terminate
                        
                        killed_count += 1
                        logger.info(f"Successfully terminated PID {proc.pid}")
                    except Exception as e:
                        logger.error(f"Error killing process {proc.pid}: {e}")
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess) as e:
            logger.warning(f"Error accessing process: {e}")
    
    logger.info(f"Killed {killed_count} bot-related processes")
    # Wait a moment to ensure all processes are terminated
    time.sleep(2)
    
    return killed_count

def reset_database():
    """Delete the existing database file and recreate it."""
    
    db_file = 'novi_sad_game.db'
    
    # Check if file exists
    if os.path.exists(db_file):
        logger.info(f"Removing existing database file: {db_file}")
        try:
            os.remove(db_file)
            logger.info("Database file removed successfully")
        except Exception as e:
            logger.error(f"Error removing database file: {e}")
            return False
    
    # Check for database journal files and remove those too
    for journal_ext in ['-journal', '-wal', '-shm']:
        journal_file = db_file + journal_ext
        if os.path.exists(journal_file):
            try:
                os.remove(journal_file)
                logger.info(f"Removed journal file: {journal_file}")
            except Exception as e:
                logger.error(f"Error removing journal file {journal_file}: {e}")
    
    # Initialize the database
    logger.info("Initializing database...")
    try:
        subprocess.run(
            [sys.executable, "init_db.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Database initialized successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error initializing database: {e}")
        logger.error(f"Output: {e.stdout}\nError: {e.stderr}")
        return False

def setup_novi_sad():
    """Set up Novi Sad districts and politicians."""
    
    # Create districts
    logger.info("Setting up Novi Sad districts...")
    try:
        districts_result = subprocess.run(
            [sys.executable, "create_districts.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Districts created successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating districts: {e}")
        logger.error(f"Output: {e.stdout}\nError: {e.stderr}")
        return False
    
    # Create politicians
    logger.info("Setting up Novi Sad politicians...")
    try:
        politicians_result = subprocess.run(
            [sys.executable, "create_politicians.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Politicians created successfully")
    except subprocess.CalledProcessError as e:
        logger.error(f"Error creating politicians: {e}")
        logger.error(f"Output: {e.stdout}\nError: {e.stderr}")
        return False
    
    # Verify setup
    logger.info("Verifying Novi Sad setup...")
    try:
        verify_result = subprocess.run(
            [sys.executable, "check_novi_sad_setup.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info("Setup verification completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error verifying setup: {e}")
        logger.error(f"Output: {e.stdout}\nError: {e.stderr}")
        return False

def start_bot_background():
    """Start the bot in the background."""
    
    logger.info("Starting bot in the background...")
    try:
        # Use the improved background service runner
        subprocess.Popen(
            [sys.executable, "run_bg_service.py"],
            stdout=open('service.log', 'w'),
            stderr=subprocess.STDOUT
        )
        
        logger.info("Bot started in the background. Check service.log for details.")
        return True
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("🔄 Reset and Run Novi Sad Game Bot")
    print("=" * 50)
    
    # Step 1: Kill any existing bot processes
    print("\n1. Killing any existing bot processes...")
    kill_all_bot_processes()
    
    # Step 2: Reset the database
    print("\n2. Resetting database...")
    if not reset_database():
        print("❌ Failed to reset database. Check reset.log for details.")
        sys.exit(1)
    
    # Step 3: Set up Novi Sad
    print("\n3. Setting up Novi Sad...")
    if not setup_novi_sad():
        print("❌ Failed to set up Novi Sad. Check reset.log for details.")
        sys.exit(1)
    
    # Step 4: Start the bot
    print("\n4. Starting the bot...")
    if not start_bot_background():
        print("❌ Failed to start the bot. Check reset.log for details.")
        sys.exit(1)
    
    print("\n✅ Novi Sad Game Bot reset and started successfully!")
    print("Use 'tail -f service.log' to monitor the bot logs.") 