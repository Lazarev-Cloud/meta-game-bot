#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Main bot file for Belgrade Game Bot
"""

import logging
import os
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ConversationHandler
)
from commands import (
    start_command,
    help_command,
    status_command,
    action_command,
    quick_action_command,
    cancel_action_command,
    actions_left_command,
    view_district_command,
    resources_command,
    convert_resource_command,
    check_income_command,
    time_command,
    news_command,
    map_command,
    politicians_command,
    politician_status_command,
    international_command,
    trade_command,
    accept_trade_command,
    set_location_command,
    admin_commands
)
from language_command import language_command, language_callback
from languages import init_language_support
from language_utils import detect_user_language
from config import TOKEN

# Enable logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

logger = logging.getLogger(__name__)

async def error_handler(update, context):
    """Log errors caused by updates."""
    logger.error(f"Update {update} caused error {context.error}")

def main():
    """Start the bot."""
    # Initialize language support
    init_language_support()

    # Create the Application
    application = Application.builder().token(TOKEN).build()

    # Add command handlers
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("status", status_command))
    application.add_handler(CommandHandler("action", action_command))
    application.add_handler(CommandHandler("quick_action", quick_action_command))
    application.add_handler(CommandHandler("cancel_action", cancel_action_command))
    application.add_handler(CommandHandler("actions_left", actions_left_command))
    application.add_handler(CommandHandler("view_district", view_district_command))
    application.add_handler(CommandHandler("resources", resources_command))
    application.add_handler(CommandHandler("convert_resource", convert_resource_command))
    application.add_handler(CommandHandler("check_income", check_income_command))
    application.add_handler(CommandHandler("time", time_command))
    application.add_handler(CommandHandler("news", news_command))
    application.add_handler(CommandHandler("map", map_command))
    application.add_handler(CommandHandler("politicians", politicians_command))
    application.add_handler(CommandHandler("politician_status", politician_status_command))
    application.add_handler(CommandHandler("international", international_command))
    application.add_handler(CommandHandler("trade", trade_command))
    application.add_handler(CommandHandler("accept_trade", accept_trade_command))
    application.add_handler(CommandHandler("set_location", set_location_command))
    application.add_handler(CommandHandler("language", language_command))

    # Add admin command handlers
    for command, handler in admin_commands.items():
        application.add_handler(CommandHandler(command, handler))

    # Add callback query handler for language selection
    application.add_handler(CallbackQueryHandler(language_callback, pattern=r'^lang:'))

    # Add error handler
    application.add_error_handler(error_handler)

    # Start the Bot
    application.run_polling()

if __name__ == '__main__':
    main() 