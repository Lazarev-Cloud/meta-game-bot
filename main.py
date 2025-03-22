#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Meta Game - Telegram Bot
A political strategy game set in Novi-Sad, Yugoslavia in 1999.
"""

import logging
import os
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters,
)

# Import bot components
from bot.commands import register_commands
from bot.callbacks import register_callbacks
from bot.middleware import setup_middleware
from bot.states import conversation_handlers

# Import database client
from db.supabase_client import init_supabase

# Import utility functions
from utils.logger import setup_logger
from utils.config import load_config
from utils.i18n import setup_i18n, _

# Load environment variables
load_dotenv()

# Setup logging
logger = setup_logger()

async def error_handler(update, context):
    """Handle errors in the dispatcher."""
    logger.error(f"Exception while handling an update: {context.error}")
    if update and update.effective_message:
        await update.effective_message.reply_text(
            "An error occurred while processing your request. Please try again later."
        )

def main():
    """Initialize and start the bot."""
    # Load bot token
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("No bot token found. Please set TELEGRAM_BOT_TOKEN in .env file.")
        return
    
    # Load admin IDs
    admin_ids_str = os.getenv("TELEGRAM_ADMIN_IDS", "")
    admin_ids = [int(id_str) for id_str in admin_ids_str.split(",") if id_str]
    
    # Load configuration
    config = load_config()
    
    # Initialize Supabase client
    init_supabase()
    
    # Set up internationalization
    setup_i18n()
    
    # Initialize the Application
    application = Application.builder().token(token).build()
    
    # Set up middleware
    setup_middleware(application, admin_ids)
    
    # Register command handlers
    register_commands(application)
    
    # Register callback query handlers
    register_callbacks(application)
    
    # Add conversation handlers
    for handler in conversation_handlers:
        application.add_handler(handler)
    
    # Register error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Starting Meta Game bot...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()