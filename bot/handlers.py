#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Unified handler registration for the Meta Game bot.
This module centralizes command and callback registration logic.
"""

import logging
from typing import Dict, List, Callable, Any, Optional

from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ConversationHandler,
    MessageHandler,
    filters
)

# Initialize logger
logger = logging.getLogger(__name__)


class HandlerRegistry:
    """Central registry for all bot handlers."""

    def __init__(self):
        self.command_handlers: Dict[str, Callable] = {}
        self.callback_handlers: Dict[str, Callable] = {}
        self.conversation_handlers: List[ConversationHandler] = []
        self.message_handlers: List[MessageHandler] = []
        self.other_handlers: List[Any] = []
        self._added_commands = set()  # Track commands already added via conversations

    def register_command(self, command: str, handler: Callable) -> None:
        """Register a command handler."""
        self.command_handlers[command] = handler
        logger.debug(f"Registered command handler: /{command}")

    def register_callback(self, pattern: str, handler: Callable) -> None:
        """Register a callback query handler with regex pattern."""
        self.callback_handlers[pattern] = handler
        logger.debug(f"Registered callback handler with pattern: {pattern}")

    def register_conversation(self, conversation_handler: ConversationHandler) -> None:
        """Register a conversation handler."""
        self.conversation_handlers.append(conversation_handler)
        logger.debug(f"Registered conversation handler")

    def register_message_handler(self, message_handler: MessageHandler) -> None:
        """Register a general message handler."""
        self.message_handlers.append(message_handler)
        logger.debug(f"Registered message handler")

    def register_other_handler(self, handler: Any) -> None:
        """Register any other type of handler."""
        self.other_handlers.append(handler)
        logger.debug(f"Registered other handler: {type(handler).__name__}")

    def apply_handlers(self, application: Application) -> None:
        """Apply all registered handlers to the application in correct order."""
        # Apply conversation handlers first (highest priority)
        for handler in self.conversation_handlers:
            application.add_handler(handler)

            # Track commands that are entry points in conversations
            for entry_point in handler.entry_points:
                if isinstance(entry_point, CommandHandler):
                    for cmd in entry_point.command:
                        self._added_commands.add(cmd)

        # Add command handlers that aren't part of conversations
        for command, handler in self.command_handlers.items():
            if command not in self._added_commands:
                application.add_handler(CommandHandler(command, handler))

        # Add callback handlers
        for pattern, handler in self.callback_handlers.items():
            application.add_handler(CallbackQueryHandler(handler, pattern=pattern))

        # Add message handlers
        for handler in self.message_handlers:
            application.add_handler(handler)

        # Add other handlers
        for handler in self.other_handlers:
            application.add_handler(handler)

        logger.info(
            f"Applied {len(self.command_handlers)} commands, {len(self.callback_handlers)} callbacks, "
            f"{len(self.conversation_handlers)} conversations, {len(self.message_handlers)} message handlers, "
            f"and {len(self.other_handlers)} other handlers"
        )


# Create a global handler registry
handler_registry = HandlerRegistry()


# Helper function to register all handlers
def register_all_handlers(application: Application) -> None:
    """Register all handlers from commands, callbacks, and states modules."""
    # Import and register command handlers
    from bot.commands import register_commands
    register_commands(handler_registry)

    # Import and register callback handlers
    from bot.callbacks import register_callbacks
    register_callbacks(handler_registry)

    # Import and register conversation handlers
    from bot.states import conversation_handlers
    for handler in conversation_handlers:
        handler_registry.register_conversation(handler)

    # Apply all registered handlers to the application
    handler_registry.apply_handlers(application)

    logger.info("All handlers registered successfully")