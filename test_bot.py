#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Test script for Belgrade Game Bot
Validates core functionality and language support
"""

import logging
import sys
import os
import unittest
from unittest.mock import MagicMock, patch
from typing import Any, Dict, List, Optional

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
from db.schema import initialize_database, initialize_basic_data
from db.queries import db_connection_pool, cleanup_database_pool
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

        # Create a test-specific connection pool
        cls.test_pool = DatabaseConnectionPool(
            db_path=cls.test_db,
            max_connections=5,
            timeout=5.0
        )

        # Replace the global connection pool with our test pool
        cls.original_pool = db_connection_pool
        db_connection_pool = cls.test_pool

        # Initialize database
        initialize_database()

        # Initialize language support
        init_language_support()

    @classmethod
    def tearDownClass(cls):
        """Clean up after tests"""
        logger.info("Cleaning up test environment")

        # Restore original connection pool
        db_connection_pool = cls.original_pool

        # Clean up test pool
        cls.test_pool.close_all_connections()

        # Remove test database
        if os.path.exists(cls.test_db):
            os.remove(cls.test_db)

    def setUp(self):
        """Set up before each test"""
        # Get a connection for the test
        self.conn = db_connection_pool.get_connection()

    def tearDown(self):
        """Clean up after each test"""
        # Return the connection to the pool
        db_connection_pool.return_connection(self.conn)

    def test_database_setup(self):
        """Test database setup created required tables"""
        cursor = self.conn.cursor()

        # Check essential tables exist
        essential_tables = [
            'players', 'districts', 'politicians', 'resources',
            'politician_relationships', 'resource_types', 'languages',
            'commands', 'news', 'trades', 'joint_actions'
        ]
        for table in essential_tables:
            cursor.execute(f"SELECT name FROM sqlite_master WHERE type='table' AND name='{table}'")
            self.assertIsNotNone(cursor.fetchone(), f"Table {table} not found")

    def test_resource_validation(self):
        """Test resource validation functions"""
        # Test resource type validation
        self.assertTrue(validate_resource_type('money'))
        self.assertTrue(validate_resource_type('influence'))
        self.assertTrue(validate_resource_type('support'))
        self.assertFalse(validate_resource_type('invalid_resource'))

        # Test resource amount validation
        valid, amount, _ = validate_resource_amount(100)
        self.assertTrue(valid)
        self.assertEqual(amount, 100)

        valid, amount, _ = validate_resource_amount(-50)
        self.assertFalse(valid)
        self.assertEqual(amount, 0)

        valid, amount, _ = validate_resource_amount('invalid')
        self.assertFalse(valid)
        self.assertEqual(amount, 0)

    def test_character_name_validation(self):
        """Test character name validation"""
        # Test valid names
        valid, _ = validate_character_name("John Doe")
        self.assertTrue(valid)

        valid, _ = validate_character_name("Player_123")
        self.assertTrue(valid)

        # Test invalid names
        valid, _ = validate_character_name("")
        self.assertFalse(valid)

        valid, _ = validate_character_name("a")  # Too short
        self.assertFalse(valid)

        valid, _ = validate_character_name("a" * 31)  # Too long
        self.assertFalse(valid)

        valid, _ = validate_character_name("Invalid<Name>")  # Invalid characters
        self.assertFalse(valid)

    def test_language_support(self):
        """Test language support functionality"""
        # Test language detection
        lang = detect_language_from_message("Hello")
        self.assertEqual(lang, "en")

        lang = detect_language_from_message("Здравствуйте")
        self.assertEqual(lang, "ru")

        lang = detect_language_from_message("Здраво")
        self.assertEqual(lang, "sr")

        # Test keyboard translation
        keyboard = get_translated_keyboard("en")
        self.assertIsNotNone(keyboard)
        self.assertTrue(isinstance(keyboard, list))

        keyboard = get_translated_keyboard("ru")
        self.assertIsNotNone(keyboard)
        self.assertTrue(isinstance(keyboard, list))

        keyboard = get_translated_keyboard("sr")
        self.assertIsNotNone(keyboard)
        self.assertTrue(isinstance(keyboard, list))

    def test_database_queries(self):
        """Test database queries with connection pool"""
        cursor = self.conn.cursor()

        # Test player creation
        cursor.execute("""
            INSERT INTO players (username, ideology_score)
            VALUES (?, ?)
        """, ("test_player", 50))
        player_id = cursor.lastrowid
        self.assertIsNotNone(player_id)

        # Test politician creation
        cursor.execute("""
            INSERT INTO politicians (name, role, ideology_score)
            VALUES (?, ?, ?)
        """, ("Test Politician", "Mayor", 60))
        politician_id = cursor.lastrowid
        self.assertIsNotNone(politician_id)

        # Test district creation
        cursor.execute("""
            INSERT INTO districts (name, description, control_points)
            VALUES (?, ?, ?)
        """, ("Test District", "A test district", 10))
        district_id = cursor.lastrowid
        self.assertIsNotNone(district_id)

        # Test resource allocation
        cursor.execute("""
            INSERT INTO player_resources (player_id, resource_type, amount)
            VALUES (?, ?, ?)
        """, (player_id, "money", 1000))
        self.conn.commit()

        # Verify data
        cursor.execute("SELECT username FROM players WHERE player_id = ?", (player_id,))
        self.assertEqual(cursor.fetchone()[0], "test_player")

        cursor.execute("SELECT name FROM politicians WHERE politician_id = ?", (politician_id,))
        self.assertEqual(cursor.fetchone()[0], "Test Politician")

        cursor.execute("SELECT name FROM districts WHERE district_id = ?", (district_id,))
        self.assertEqual(cursor.fetchone()[0], "Test District")

        cursor.execute("""
            SELECT amount FROM player_resources 
            WHERE player_id = ? AND resource_type = ?
        """, (player_id, "money"))
        self.assertEqual(cursor.fetchone()[0], 1000)


if __name__ == '__main__':
    unittest.main()