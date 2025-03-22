#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Bot module for the Meta Game bot.
"""

from bot.callbacks import register_callbacks
from bot.commands import register_commands
from bot.keyboards import (
    get_start_keyboard,
    get_help_keyboard,
    get_status_keyboard,
    get_map_keyboard,
    get_action_keyboard,
    get_quick_action_keyboard,
    get_districts_keyboard,
    get_resources_keyboard,
    get_politicians_keyboard,
    get_politician_interaction_keyboard,
    get_resource_type_keyboard,
    get_resource_amount_keyboard,
    get_confirmation_keyboard,
    get_yes_no_keyboard,
    get_physical_presence_keyboard,
    get_back_keyboard,
    get_language_keyboard,
    get_collective_action_keyboard
)
from bot.middleware import setup_middleware
from bot.states import (
    NAME_ENTRY,
    IDEOLOGY_CHOICE,
    ACTION_SELECT_DISTRICT,
    ACTION_SELECT_TARGET,
    ACTION_SELECT_RESOURCE,
    ACTION_SELECT_AMOUNT,
    ACTION_PHYSICAL_PRESENCE,
    ACTION_CONFIRM,
    CONVERT_FROM_RESOURCE,
    CONVERT_TO_RESOURCE,
    CONVERT_AMOUNT,
    CONVERT_CONFIRM,
    COLLECTIVE_ACTION_TYPE,
    COLLECTIVE_ACTION_DISTRICT,
    COLLECTIVE_ACTION_TARGET,
    COLLECTIVE_ACTION_RESOURCE,
    COLLECTIVE_ACTION_AMOUNT,
    COLLECTIVE_ACTION_PHYSICAL,
    COLLECTIVE_ACTION_CONFIRM,
    JOIN_ACTION_RESOURCE,
    JOIN_ACTION_AMOUNT,
    JOIN_ACTION_PHYSICAL,
    JOIN_ACTION_CONFIRM,
    registration_handler,
    action_handler,
    resource_conversion_handler,
    conversation_handlers
)

__all__ = [
    'register_commands',
    'register_callbacks',
    'setup_middleware',
    'get_start_keyboard',
    'get_help_keyboard',
    'get_status_keyboard',
    'get_map_keyboard',
    'get_action_keyboard',
    'get_quick_action_keyboard',
    'get_districts_keyboard',
    'get_resources_keyboard',
    'get_politicians_keyboard',
    'get_politician_interaction_keyboard',
    'get_resource_type_keyboard',
    'get_resource_amount_keyboard',
    'get_confirmation_keyboard',
    'get_yes_no_keyboard',
    'get_physical_presence_keyboard',
    'get_back_keyboard',
    'get_language_keyboard',
    'get_collective_action_keyboard',
    'NAME_ENTRY',
    'IDEOLOGY_CHOICE',
    'ACTION_SELECT_DISTRICT',
    'ACTION_SELECT_TARGET',
    'ACTION_SELECT_RESOURCE',
    'ACTION_SELECT_AMOUNT',
    'ACTION_PHYSICAL_PRESENCE',
    'ACTION_CONFIRM',
    'CONVERT_FROM_RESOURCE',
    'CONVERT_TO_RESOURCE',
    'CONVERT_AMOUNT',
    'CONVERT_CONFIRM',
    'COLLECTIVE_ACTION_TYPE',
    'COLLECTIVE_ACTION_DISTRICT',
    'COLLECTIVE_ACTION_TARGET',
    'COLLECTIVE_ACTION_RESOURCE',
    'COLLECTIVE_ACTION_AMOUNT',
    'COLLECTIVE_ACTION_PHYSICAL',
    'COLLECTIVE_ACTION_CONFIRM',
    'JOIN_ACTION_RESOURCE',
    'JOIN_ACTION_AMOUNT',
    'JOIN_ACTION_PHYSICAL',
    'JOIN_ACTION_CONFIRM',
    'registration_handler',
    'action_handler',
    'resource_conversion_handler',
    'conversation_handlers'
]
