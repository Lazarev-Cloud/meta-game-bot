# Language support for Belgrade Game Bot
# This file contains translations for all bot messages
import logging
import sqlite3

from languages_base import (
    TRANSLATIONS, RESOURCE_NAMES, CYCLE_NAMES, ACTION_NAMES,
    get_text, get_resource_name, get_cycle_name, get_action_name, get_district_name
)
from languages_update import (
    update_translations, update_admin_translations, 
    init_language_support
)

logger = logging.getLogger(__name__)

# Player language retrieval function for main.py
def get_player_language(player_id):
    """Get player's preferred language"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        cursor.execute("SELECT language FROM players WHERE player_id = ?", (player_id,))
        result = cursor.fetchone()
        conn.close()

        if result:
            return result[0]
        else:
            logger.warning(f"No language found for player {player_id}, defaulting to English")
            return "en"  # Default to English
    except Exception as e:
        logger.error(f"Error getting player language for player {player_id}: {e}")
        return "en"  # Default to English on error

def set_player_language(player_id, language):
    """Set player's preferred language"""
    try:
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()

        # Check if player exists
        cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (player_id,))
        player_exists = cursor.fetchone() is not None

        if player_exists:
            cursor.execute(
                "UPDATE players SET language = ? WHERE player_id = ?",
                (language, player_id)
            )
            rows_affected = cursor.rowcount
            conn.commit()
            conn.close()

            if rows_affected == 0:
                logger.warning(f"Failed to update language for player {player_id}. No rows affected.")
                return False
            logger.info(f"Language updated to {language} for player {player_id}")
            return True
        else:
            # Player doesn't exist, this might happen if set_player_language is called before registration
            logger.warning(f"Tried to set language for non-existent player {player_id}")
            conn.close()
            return False
    except Exception as e:
        logger.error(f"Error setting player language for player {player_id}: {e}")
        try:
            conn.close()
        except:
            pass
        return False

def format_ideology(ideology_score, lang="en"):
    """Get formatted ideology description based on score"""
    if ideology_score > 3:
        return get_text("ideology_strongly_conservative", lang)
    elif ideology_score > 0:
        return get_text("ideology_conservative", lang)
    elif ideology_score == 0:
        return get_text("ideology_neutral", lang)
    elif ideology_score > -3:
        return get_text("ideology_reformist", lang)
    else:
        return get_text("ideology_strongly_reformist", lang)

def check_missing_translations():
    """Check for missing translations and log warnings."""
    logging.info("Checking for missing translations...")
    missing_count = 0

    # Get all keys in English
    english_keys = set(TRANSLATIONS["en"].keys())

    # Check each language
    for lang in TRANSLATIONS:
        if lang == "en":
            continue

        lang_keys = set(TRANSLATIONS[lang].keys())
        missing_keys = english_keys - lang_keys

        if missing_keys:
            missing_count += len(missing_keys)
            logging.warning(f"Found {len(missing_keys)} missing translations in {lang}:")
            for key in missing_keys:
                TRANSLATIONS[lang][key] = TRANSLATIONS["en"][key]  # Use English as fallback
                logging.warning(f"  - '{key}' (using English fallback)")

    logging.info(f"Translation check complete. Fixed {missing_count} missing translations.")

# Initialize the language system
def initialize():
    """Initialize the language system"""
    init_language_support()
    check_missing_translations()
    logger.info("Language system initialized")