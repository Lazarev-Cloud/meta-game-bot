#!/usr/bin/env python3
import os
import sys
import subprocess
import logging

logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def setup_novi_sad():
    """Set up the Novi Sad game environment."""
    try:
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
        
        # Start the bot
        print("🚀 Starting Novi Sad Game Bot...")
        bot_process = subprocess.run(
            [sys.executable, "main.py"],
            check=True
        )
        
        return True
    except KeyboardInterrupt:
        print("\n⏹️ Bot stopped by user")
        return True
    except subprocess.CalledProcessError as e:
        print(f"Error running the bot: {e}")
        return False

if __name__ == "__main__":
    print("=====================================")
    print("🎮 Novi Sad Game - Yugoslavia 1990s 🎮")
    print("=====================================")
    
    # Check if we should skip setup
    skip_setup = "--skip-setup" in sys.argv
    
    if not skip_setup:
        print("\n📋 Running Novi Sad setup...")
        if not setup_novi_sad():
            print("\n❌ Setup failed! Please check the errors above.")
            sys.exit(1)
        print("\n✅ Novi Sad setup completed successfully!")
    else:
        print("\n🔄 Skipping setup (--skip-setup flag detected)")
    
    print("\n🚀 Starting the game...")
    success = run_game()
    
    if success:
        print("\n✅ Game session ended")
        sys.exit(0)
    else:
        print("\n❌ Game session failed")
        sys.exit(1) 