#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Constants and shared state for the Meta Game bot.
"""

# Define conversation states
(
    # Registration states
    NAME_ENTRY,
    IDEOLOGY_CHOICE,

    # Action selection states
    ACTION_SELECT_DISTRICT,
    ACTION_SELECT_TARGET,
    ACTION_SELECT_RESOURCE,
    ACTION_SELECT_AMOUNT,
    ACTION_PHYSICAL_PRESENCE,
    ACTION_CONFIRM,

    # Resource conversion states
    CONVERT_FROM_RESOURCE,
    CONVERT_TO_RESOURCE,
    CONVERT_AMOUNT,
    CONVERT_CONFIRM,

    # Collective action states
    COLLECTIVE_ACTION_TYPE,
    COLLECTIVE_ACTION_DISTRICT,
    COLLECTIVE_ACTION_TARGET,
    COLLECTIVE_ACTION_RESOURCE,
    COLLECTIVE_ACTION_AMOUNT,
    COLLECTIVE_ACTION_PHYSICAL,
    COLLECTIVE_ACTION_CONFIRM,

    # Join collective action states
    JOIN_ACTION_RESOURCE,
    JOIN_ACTION_AMOUNT,
    JOIN_ACTION_PHYSICAL,
    JOIN_ACTION_CONFIRM
) = range(23)
