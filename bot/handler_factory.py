#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Handler factory for creating command handlers with proper error handling.
"""

import logging
from typing import Callable, List, Any, Dict

from telegram.ext import CommandHandler, MessageHandler, filters

from utils.error_handling import conversation_step

# Initialize logger
logger = logging.getLogger(__name__)


def get_command_handler(command: str, handler_func: Callable) -> CommandHandler:
    """
    Create a command handler with error handling applied.

    This applies the conversation_step decorator to ensure proper
    error handling for all command handlers.
    """
    # Wrap handler with conversation_step decorator if it's not already
    if not hasattr(handler_func, '_conversation_step_applied'):
        handler_func = conversation_step(handler_func)

    return CommandHandler(command, handler_func)


def get_message_handler(filter_type: Any, handler_func: Callable) -> MessageHandler:
    """
    Create a message handler with error handling applied.

    This applies the conversation_step decorator to ensure proper
    error handling for all message handlers.
    """
    # Wrap handler with conversation_step decorator if it's not already
    if not hasattr(handler_func, '_conversation_step_applied'):
        handler_func = conversation_step(handler_func)

    return MessageHandler(filter_type, handler_func)


def get_resource_command_handler():
    """
    Create a resource command handler with proper error handling.
    """
    from bot.commands import resource_conversion_command
    return get_command_handler("convert_resource", resource_conversion_command)


def create_command_handlers(commands_dict: Dict[str, Callable]) -> List[CommandHandler]:
    """
    Create multiple command handlers from a dictionary mapping command names to handler functions.

    Args:
        commands_dict: Dictionary mapping command names to handler functions

    Returns:
        List of CommandHandler objects
    """
    handlers = []

    for command, handler_func in commands_dict.items():
        handlers.append(get_command_handler(command, handler_func))
        logger.debug(f"Created command handler for /{command}")

    return handlers


def register_commands(application, commands_dict: Dict[str, Callable]) -> None:
    """
    Register multiple commands from a dictionary to an application.

    Args:
        application: Telegram Application object
        commands_dict: Dictionary mapping command names to handler functions
    """
    for command, handler_func in commands_dict.items():
        application.add_handler(get_command_handler(command, handler_func))
        logger.debug(f"Registered command handler for /{command}")