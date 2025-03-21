#!/usr/bin/env python3
"""
Comprehensive cleanup script for the Novi Sad Game Bot
This script:
1. Resets the Telegram webhook
2. Cleans up all related processes
3. Removes lock files from common locations
"""

import os
import sys
import time
import logging
import requests
import subprocess
import glob
from pathlib import Path

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(), logging.FileHandler("cleanup.log")]
)
logger = logging.getLogger(__name__)

def reset_telegram_webhook():
    """Reset the Telegram webhook to prevent conflicts"""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    
    # If not in environment, try to read from .env file
    if not token:
        try:
            with open(".env") as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.strip().split("=", 1)[1].strip()
                        # Remove quotes if present
                        if token.startswith('"') and token.endswith('"'):
                            token = token[1:-1]
                        elif token.startswith("'") and token.endswith("'"):
                            token = token[1:-1]
                        break
        except Exception as e:
            logger.error(f"Failed to read .env file: {e}")
    
    if not token:
        logger.warning("No Telegram token found, skipping webhook reset")
        return False
    
    # Make three attempts to reset the webhook
    for attempt in range(3):
        try:
            logger.info(f"Resetting Telegram webhook (attempt {attempt+1}/3)...")
            
            # First, get current webhook info
            try:
                info_response = requests.get(
                    f"https://api.telegram.org/bot{token}/getWebhookInfo",
                    timeout=10
                )
                
                if info_response.status_code == 200:
                    webhook_info = info_response.json()
                    if webhook_info.get('ok'):
                        current_webhook = webhook_info.get('result', {}).get('url', 'None')
                        logger.info(f"Current webhook URL: {current_webhook}")
                except Exception as e:
                    logger.warning(f"Failed to get webhook info: {e}")
            
            # Then delete the webhook
            response = requests.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook",
                params={"drop_pending_updates": True},
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info("Webhook reset successfully")
                    
                    # Verify the webhook was actually deleted
                    try:
                        verify_response = requests.get(
                            f"https://api.telegram.org/bot{token}/getWebhookInfo",
                            timeout=10
                        )
                        
                        if verify_response.status_code == 200:
                            verify_result = verify_response.json()
                            if verify_result.get('ok'):
                                webhook_url = verify_result.get('result', {}).get('url', '')
                                if not webhook_url:
                                    logger.info("Webhook deletion verified: no webhook is set")
                                    return True
                                else:
                                    logger.warning(f"Webhook still exists after deletion attempt: {webhook_url}")
                    except Exception as e:
                        logger.warning(f"Failed to verify webhook deletion: {e}")
                    
                    # Return True even if verification fails, since the API said it succeeded
                    return True
                else:
                    error_description = result.get('description', 'Unknown error')
                    logger.error(f"Telegram API returned error: {error_description}")
            else:
                logger.error(f"Failed to reset webhook: HTTP {response.status_code} - {response.text}")
            
            # Wait before retry
            if attempt < 2:  # Don't wait after the last attempt
                time.sleep(2)
        
        except requests.RequestException as e:
            logger.error(f"Network error resetting webhook: {e}")
            
            # Wait before retry
            if attempt < 2:  # Don't wait after the last attempt
                time.sleep(3)
        except Exception as e:
            logger.error(f"Unexpected error resetting webhook: {e}")
            
            # Wait before retry
            if attempt < 2:  # Don't wait after the last attempt
                time.sleep(3)
    
    # If we get here, all attempts failed
    logger.error("All attempts to reset the webhook failed")
    return False

def kill_processes():
    """Kill all processes related to the bot"""
    processes_to_kill = [
        "python.*main.py",
        "python.*run_bg_service.py",
        "python.*novi_sad",
        "python.*bot",
        ".*getUpdates",
        "telegram.org"
    ]
    
    logger.info("Killing bot-related processes...")
    
    # First try normal termination
    for pattern in processes_to_kill:
        try:
            subprocess.run(["pkill", "-f", pattern], stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error killing processes matching '{pattern}': {e}")
    
    # Wait for processes to terminate
    time.sleep(2)
    
    # Then try forceful termination for any remaining processes
    for pattern in processes_to_kill:
        try:
            subprocess.run(["pkill", "-9", "-f", pattern], stderr=subprocess.DEVNULL)
        except Exception as e:
            logger.error(f"Error force killing processes matching '{pattern}': {e}")
    
    # Wait again for processes to terminate
    time.sleep(2)
    
    # Find and kill processes directly with OS calls for more reliability
    try:
        # Get all Python processes
        process_cmd = "ps aux | grep -E 'python.*main.py|python.*run_bg_service.py|python.*novi_sad|.*getUpdates|telegram.org' | grep -v grep || true"
        result = subprocess.run(process_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.stdout.strip():
            logger.warning("Found processes that need to be killed directly:")
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    try:
                        logger.info(f"Killing process {pid} directly")
                        subprocess.run(["kill", "-9", pid], stderr=subprocess.DEVNULL)
                    except Exception as e:
                        logger.error(f"Error killing process {pid}: {e}")
    except Exception as e:
        logger.error(f"Error in direct process killing: {e}")
    
    # Special case for Python processes as a last resort
    try:
        # Only kill Python processes if we specifically detect telegram bot related ones still running
        check_cmd = "ps aux | grep -E 'python.*main.py|python.*run_bg_service.py|.*getUpdates|telegram.org' | grep -v grep || true"
        result = subprocess.run(check_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.stdout.strip():
            logger.warning("Still found telegram-related processes, attempting killall as last resort")
            subprocess.run(["killall", "-9", "Python"], stderr=subprocess.DEVNULL)
        else:
            logger.info("No remaining telegram bot processes found, skipping killall")
    except Exception as e:
        logger.error(f"Error running killall: {e}")
    
    time.sleep(2)  # Wait for processes to terminate
    
    # Final verification
    try:
        # Check if any bot-related processes are still running
        verify_cmd = "ps aux | grep -E 'python.*main.py|python.*run_bg_service.py|python.*novi_sad|.*getUpdates|telegram.org' | grep -v grep || true"
        result = subprocess.run(verify_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        
        if result.stdout.strip():
            remaining_processes = result.stdout.strip()
            logger.warning(f"These processes are still running after cleanup attempts:\n{remaining_processes}")
            
            # Extract and try to kill each process individually one last time
            for line in result.stdout.splitlines():
                parts = line.split()
                if len(parts) >= 2:
                    pid = parts[1]
                    try:
                        logger.info(f"Final attempt to kill process {pid}")
                        os.kill(int(pid), 9)
                    except:
                        pass
        else:
            logger.info("No bot processes found running after cleanup")
    except Exception as e:
        logger.error(f"Error in final process verification: {e}")
        
    # Reset the Telegram webhook to ensure clean connections
    reset_telegram_webhook()

def cleanup_lock_files():
    """Remove lock files from common locations"""
    lock_patterns = [
        "/tmp/novi_sad_*.lock",
        "/tmp/novi_sad_bot.lock",
        "/tmp/novi_sad_bg_service.lock",
        "/tmp/novi_sad_game.lock",
        "/var/folders/**/novi_sad_*.lock",
        "~/Library/Caches/*novi_sad*.lock",
        "/private/tmp/novi_sad_*.lock",
        "/private/var/folders/**/novi_sad_*.lock"
    ]
    
    logger.info("Cleaning up lock files...")
    
    for pattern in lock_patterns:
        try:
            # Use glob for simple patterns
            for lock_file in glob.glob(os.path.expanduser(pattern)):
                try:
                    os.remove(lock_file)
                    logger.info(f"Removed lock file: {lock_file}")
                except Exception as e:
                    logger.error(f"Failed to remove lock file {lock_file}: {e}")
        except Exception as e:
            logger.error(f"Error processing pattern {pattern}: {e}")
    
    # Look for any files containing 'novi_sad' in /var
    try:
        subprocess.run(
            "find /var -name '*novi_sad*' -type f -delete 2>/dev/null || true",
            shell=True
        )
    except Exception as e:
        logger.error(f"Error finding additional lock files: {e}")

def main():
    """Run all cleanup operations"""
    logger.info("Starting comprehensive cleanup...")
    
    # Kill processes first
    kill_processes()
    
    # Reset Telegram webhook
    reset_telegram_webhook()
    
    # Clean up lock files
    cleanup_lock_files()
    
    # Final verification
    logger.info("Cleanup completed")
    
    return 0

if __name__ == "__main__":
    sys.exit(main()) 