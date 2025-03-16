import os

# Load the Telegram Bot API Token from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

if TOKEN is None:
    raise ValueError("The TELEGRAM_BOT_TOKEN environment variable is not set.")

# Load Administrator IDs from environment variables
# Admin IDs should be a comma-separated list of IDs
ADMIN_IDS = os.getenv("TELEGRAM_ADMIN_IDS")

if ADMIN_IDS is None:
    raise ValueError("The TELEGRAM_ADMIN_IDS environment variable is not set.")
else:
    ADMIN_IDS = [int(admin_id) for admin_id in ADMIN_IDS.split(",")]

# Example usage:
print("Token:", TOKEN)
print("Admin IDs:", ADMIN_IDS)