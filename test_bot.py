#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for Belgrade Game Bot
Validates core functionality and language support
"""

import logging
import sqlite3
import sys
import os
import unittest
from unittest.mock import MagicMock, patch

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.FileHandler("test_bot.log"),
        logging.StreamHandler(sys.stdout)
    ]
)

logger = logging.getLogger(__name__)

# Import modules to test
import languages
from languages_update import init_language_support, get_translated_keyboard, detect_language_from_message
from db.schema import setup_database
from validators import (
    validate_resource_type, validate_resource_amount, validate_district_id,
    validate_politician_id, validate_character_name, validate_player_resources
)


class TestBelgradeBot(unittest.TestCase):
    """Test cases for Belgrade Game Bot"""

    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        logger.info("Setting up test environment")

        # Use a test database
        cls.test_db = 'test_belgrade_game.db'

        # Patch the database file path
        cls.db_patch = patch('sqlite3.connect', return_value=sqlite3.connect(cls.test_db))
        cls.db_patch.start()

        # Initialize database
        setup_database()

        # Initialize language support
        init_language_support()

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        logger.info("Cleaning up test environment")

        # Stop database patch
        cls.db_patch.stop()

        # Remove test database
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

    def test_database_setup(self):
        """Test database setup created required tables"""
        conn = sqlite3.connect(self.test_db)
        cursor = conn.cursor()

        # Check if required tables exist
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        tables = [table[0] for table in cursor.fetchall()]

        required_tables = [
            'players', 'resources', 'districts', 'district_control',
            'politicians', 'actions', 'news', 'politician_relationships'
        ]

        for table in required_tables:
            self.assertIn(table, tables, f"Required table {table} is missing")

        # Check if districts were populated
        cursor.execute("SELECT COUNT(*) FROM districts")
        district_count = cursor.fetchone()[0]
        self.assertGreater(district_count, 0, "Districts table should be populated")

        # Check if politicians were populated
        cursor.execute("SELECT COUNT(*) FROM politicians")
        politician_count = cursor.fetchone()[0]
        self.assertGreater(politician_count, 0, "Politicians table should be populated")

        conn.close()

    def test_language_translations(self):
        """Test language translation functionality"""
        # Test basic translation
        self.assertEqual(languages.get_text("welcome", "en").startswith("Welcome"), True)
        self.assertEqual(languages.get_text("welcome", "ru").startswith("Добро"), True)

        # Test fallback to English for missing keys
        test_key = "non_existent_key"
        fallback_message = f"[Missing translation: {test_key}]"
        self.assertEqual(languages.get_text(test_key), fallback_message)

        # Test translation with formatting
        formatted_en = languages.get_text("name_set", "en", character_name="Test")
        self.assertIn("Test", formatted_en)

        formatted_ru = languages.get_text("name_set", "ru", character_name="Тест")
        self.assertIn("Тест", formatted_ru)

        # Test additional translations
        self.assertNotEqual(languages.get_text("action_pol_info", "en"), "[Missing translation: action_pol_info]")
        self.assertNotEqual(languages.get_text("action_pol_info", "ru"), "[Missing translation: action_pol_info]")

    def test_keyboard_translation(self):
        """Test keyboard translation functionality"""
        keyboard_items = [
            {"text": "action_influence", "callback_data": "influence"},
            {"text": "action_attack", "callback_data": "attack"},
            {"text": "action_defense", "callback_data": "defense"}
        ]

        # Translate to English
        en_keyboard = get_translated_keyboard(keyboard_items, "en")
        self.assertEqual(en_keyboard[0]["text"], languages.get_text("action_influence", "en"))

        # Translate to Russian
        ru_keyboard = get_translated_keyboard(keyboard_items, "ru")
        self.assertEqual(ru_keyboard[0]["text"], languages.get_text("action_influence", "ru"))

    def test_language_detection(self):
        """Test language detection functionality"""
        # English text
        self.assertEqual(detect_language_from_message("Hello, how are you?"), "en")

        # Russian text
        self.assertEqual(detect_language_from_message("Привет, как дела?"), "ru")

        # Mixed text with more English
        self.assertEqual(detect_language_from_message("Hello, привет, how are you doing today?"), "en")

        # Mixed text with more Russian
        self.assertEqual(detect_language_from_message("Привет, hello, как твои дела сегодня?"), "ru")

    def test_resource_validation(self):
        """Test resource validation functionality"""
        # Test valid resource types
        self.assertTrue(validate_resource_type("influence"))
        self.assertTrue(validate_resource_type("resources"))
        self.assertTrue(validate_resource_type("information"))
        self.assertTrue(validate_resource_type("force"))

        # Test invalid resource type
        self.assertFalse(validate_resource_type("invalid"))

        # Test resource amount validation
        valid, amount = validate_resource_amount("5")
        self.assertTrue(valid)
        self.assertEqual(amount, 5)

        valid, amount = validate_resource_amount(10)
        self.assertTrue(valid)
        self.assertEqual(amount, 10)

        valid, amount = validate_resource_amount("0")
        self.assertFalse(valid)
        self.assertEqual(amount, 0)

        valid, amount = validate_resource_amount("invalid")
        self.assertFalse(valid)
        self.assertEqual(amount, 0)

    def test_district_validation(self):
        """Test district validation functionality"""
        # Valid district ID (one from the setup)
        self.assertTrue(validate_district_id("stari_grad"))

        # Invalid district ID
        self.assertFalse(validate_district_id("nonexistent_district"))

    def test_politician_validation(self):
        """Test politician validation functionality"""
        # Valid politician ID (one from the setup)
        self.assertTrue(validate_politician_id(1))

        # Invalid politician ID
        self.assertFalse(validate_politician_id(99999))

        # Invalid type
        self.assertFalse(validate_politician_id("not_a_number"))

    def test_character_name_validation(self):
        """Test character name validation functionality"""
        # Valid names
        self.assertTrue(validate_character_name("John Doe"))
        self.assertTrue(validate_character_name("Иван Иванов"))
        self.assertTrue(validate_character_name("User123"))

        # Invalid names
        self.assertFalse(validate_character_name(""))  # Empty
        self.assertFalse(validate_character_name("a"))  # Too short
        self.assertFalse(validate_character_name("a" * 50))  # Too long
        self.assertFalse(validate_character_name("<script>alert('xss')</script>"))  # Invalid chars

    # Additional tests can be added for other functionality


if __name__ == "__main__":
    unittest.main()