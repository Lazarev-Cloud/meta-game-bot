#!/usr/bin/env python3
"""
Simple standalone script to reset the Telegram webhook.
Use this when having issues with conflicting bot instances.
"""

import os
import sys
import time
import requests
import logging
import argparse

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def reset_telegram_webhook(token, force=False, retries=3):
    """
    Reset the Telegram webhook to prevent conflicts.
    
    Args:
        token: Telegram Bot API token
        force: If True, drop all pending updates
        retries: Number of attempts to make
        
    Returns:
        bool: Success status
    """
    if not token:
        logger.error("No Telegram token provided")
        return False
    
    for attempt in range(retries):
        try:
            logger.info(f"Resetting Telegram webhook (attempt {attempt+1}/{retries})...")
            
            # First, get current webhook info
            info_response = requests.get(
                f"https://api.telegram.org/bot{token}/getWebhookInfo",
                timeout=10
            )
            
            webhook_url = None
            if info_response.status_code == 200:
                webhook_info = info_response.json()
                if webhook_info.get('ok'):
                    webhook_url = webhook_info.get('result', {}).get('url', 'None')
                    has_updates = webhook_info.get('result', {}).get('pending_update_count', 0) > 0
                    logger.info(f"Current webhook URL: {webhook_url}")
                    logger.info(f"Pending updates: {webhook_info.get('result', {}).get('pending_update_count', 0)}")
                    
                    # If no webhook is set and not forcing, we can stop
                    if not webhook_url and not force:
                        logger.info("No webhook is currently set, no action needed")
                        return True
            
            # Delete the webhook
            params = {"drop_pending_updates": force}
            logger.info(f"Deleting webhook with parameters: {params}")
            
            response = requests.post(
                f"https://api.telegram.org/bot{token}/deleteWebhook",
                params=params,
                timeout=10
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get('ok'):
                    logger.info("Webhook reset successfully")
                    
                    # Verify the webhook was actually deleted
                    verify_response = requests.get(
                        f"https://api.telegram.org/bot{token}/getWebhookInfo",
                        timeout=10
                    )
                    
                    if verify_response.status_code == 200:
                        verify_result = verify_response.json()
                        if verify_result.get('ok'):
                            final_url = verify_result.get('result', {}).get('url', '')
                            if not final_url:
                                logger.info("Webhook deletion verified: no webhook is set")
                                return True
                            else:
                                logger.warning(f"Webhook still exists after deletion attempt: {final_url}")
                                # If this was webhook URL from before, try again with more force
                                if final_url == webhook_url and not force and attempt == 0:
                                    logger.info("Retrying with force=True to drop pending updates")
                                    return reset_telegram_webhook(token, force=True, retries=2)
                    
                    # Return True even if verification fails, since the API said it succeeded
                    return True
                else:
                    error_description = result.get('description', 'Unknown error')
                    logger.error(f"Telegram API returned error: {error_description}")
            else:
                logger.error(f"Failed to reset webhook: HTTP {response.status_code} - {response.text}")
            
            # Wait before retry
            if attempt < retries - 1:
                sleep_time = 2 * (attempt + 1)  # Exponential backoff
                logger.info(f"Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
        
        except requests.RequestException as e:
            logger.error(f"Network error resetting webhook: {e}")
            
            # Wait before retry
            if attempt < retries - 1:
                sleep_time = 3 * (attempt + 1)  # Exponential backoff
                logger.info(f"Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
        
        except Exception as e:
            logger.error(f"Unexpected error resetting webhook: {e}")
            
            # Wait before retry
            if attempt < retries - 1:
                sleep_time = 3 * (attempt + 1)  # Exponential backoff
                logger.info(f"Waiting {sleep_time} seconds before retrying...")
                time.sleep(sleep_time)
    
    # If we get here, all attempts failed
    logger.error("All attempts to reset the webhook failed")
    return False

def get_token_from_env_file():
    """Extract token from .env file if available."""
    try:
        if os.path.exists(".env"):
            with open(".env") as f:
                for line in f:
                    if line.startswith("TELEGRAM_BOT_TOKEN="):
                        token = line.strip().split("=", 1)[1].strip()
                        # Remove quotes if present
                        if token.startswith('"') and token.endswith('"'):
                            token = token[1:-1]
                        elif token.startswith("'") and token.endswith("'"):
                            token = token[1:-1]
                        return token
    except Exception as e:
        logger.error(f"Failed to read .env file: {e}")
    return None

def main():
    parser = argparse.ArgumentParser(description="Reset Telegram bot webhook")
    parser.add_argument("--token", help="Telegram Bot API token")
    parser.add_argument("--force", action="store_true", help="Force deletion and drop pending updates")
    parser.add_argument("--retries", type=int, default=3, help="Number of attempts to make")
    
    args = parser.parse_args()
    
    # Get token from args, environment, or .env file
    token = args.token or os.environ.get("TELEGRAM_BOT_TOKEN") or get_token_from_env_file()
    
    if not token:
        logger.error("No Telegram token found. Please provide a token with --token, set the TELEGRAM_BOT_TOKEN environment variable, or add it to your .env file.")
        sys.exit(1)
    
    # For security, hide the actual token in logs
    safe_token = token[:8] + "..." + token[-4:] if len(token) > 12 else "****"
    logger.info(f"Using token: {safe_token}")
    
    success = reset_telegram_webhook(token, force=args.force, retries=args.retries)
    
    if success:
        logger.info("✅ Webhook has been successfully reset")
        sys.exit(0)
    else:
        logger.error("❌ Failed to reset webhook after multiple attempts")
        sys.exit(1)

if __name__ == "__main__":
    main() 