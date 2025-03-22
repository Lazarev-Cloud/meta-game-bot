#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Configuration management for the Meta Game bot.
"""

import os
import json
import logging
from typing import Dict, Any, Optional

# Initialize logger
logger = logging.getLogger(__name__)

# Default configuration values
DEFAULT_CONFIG = {
    "logging": {
        "level": "INFO",
        "format": "%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        "file": "meta_game.log"
    },
    "game": {
        "cycle_duration_hours": 6,
        "morning_deadline_hour": 12,
        "evening_deadline_hour": 18,
        "resource_exchange_ratio": 2,
        "physical_presence_bonus": 20,
        "district_control_threshold": 60,
        "strong_control_threshold": 80,
        "control_decay_per_cycle": 5,
        "max_actions_per_cycle": 1,
        "max_quick_actions_per_cycle": 2
    },
    "bot": {
        "rate_limit_requests_per_minute": 15,
        "rate_limit_warning_threshold": 3,
        "max_message_length": 4000,
        "web_map_url": "https://your-map-url.com"
    }
}

# Global configuration object
_config = None

def load_config() -> Dict[str, Any]:
    """Load configuration from file or use defaults."""
    global _config
    
    if _config is not None:
        return _config
    
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config.json"
    )
    
    # Load from file if exists
    if os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            
            # Merge with defaults (keeping file values where they exist)
            _config = merge_configs(DEFAULT_CONFIG, file_config)
            logger.info(f"Configuration loaded from {config_path}")
        except Exception as e:
            logger.error(f"Error loading configuration from {config_path}: {str(e)}")
            _config = DEFAULT_CONFIG
    else:
        # Use defaults
        _config = DEFAULT_CONFIG
        logger.info(f"No configuration file found at {config_path}, using defaults")
        
        # Save defaults for reference
        try:
            with open(config_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_CONFIG, f, indent=4)
            logger.info(f"Default configuration saved to {config_path}")
        except Exception as e:
            logger.warning(f"Could not save default configuration to {config_path}: {str(e)}")
    
    return _config

def get_config(section: Optional[str] = None, key: Optional[str] = None) -> Any:
    """Get configuration value by section and key."""
    config = load_config()
    
    if section is None:
        return config
    
    if section not in config:
        logger.warning(f"Configuration section '{section}' not found")
        return None
    
    if key is None:
        return config[section]
    
    if key not in config[section]:
        logger.warning(f"Configuration key '{key}' not found in section '{section}'")
        return None
    
    return config[section][key]

def set_config(section: str, key: str, value: Any) -> bool:
    """Set configuration value and save to file."""
    global _config
    
    config = load_config()
    
    if section not in config:
        config[section] = {}
    
    config[section][key] = value
    _config = config
    
    # Save to file
    config_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "config.json"
    )
    
    try:
        with open(config_path, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=4)
        logger.info(f"Configuration updated and saved to {config_path}")
        return True
    except Exception as e:
        logger.error(f"Error saving configuration to {config_path}: {str(e)}")
        return False

def merge_configs(default: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merge two configuration dictionaries."""
    result = default.copy()
    
    for key, value in override.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = merge_configs(result[key], value)
        else:
            result[key] = value
    
    return result