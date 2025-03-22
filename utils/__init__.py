#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Utility module for the Belgrade Game bot.
"""

from utils.i18n import _, get_user_language, set_user_language
from utils.formatting import (
    format_player_status,
    format_district_info,
    format_time,
    format_cycle_info,
    format_news,
    format_income_info,
    format_politicians_list,
    format_politician_info
)
from utils.config import load_config, get_config, set_config
from utils.logger import setup_logger, get_logger

__all__ = [
    '_',
    'get_user_language',
    'set_user_language',
    'format_player_status',
    'format_district_info',
    'format_time',
    'format_cycle_info',
    'format_news',
    'format_income_info',
    'format_politicians_list',
    'format_politician_info',
    'load_config',
    'get_config',
    'set_config',
    'setup_logger',
    'get_logger'
]