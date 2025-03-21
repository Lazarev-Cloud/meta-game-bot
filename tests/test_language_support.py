#!/usr/bin/env python3
"""
Tests for language support functionality in the Belgrade Game Bot
"""
import unittest
import sys
import os
import logging
from unittest.mock import patch, MagicMock

# Add parent directory to path to allow importing modules
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, parent_dir)

from languages import (
    TRANSLATIONS, get_text, get_resource_name, get_cycle_name, 
    get_action_name, initialize, check_missing_translations
)
from language_utils import detect_user_language, SUPPORTED_LANGUAGES

class TestLanguageTranslations(unittest.TestCase):
    """Test case for verifying language translations"""
    
    @classmethod
    def setUpClass(cls):
        """Initialize language system before tests"""
        # Disable logging during tests
        logging.disable(logging.CRITICAL)
        initialize()
    
    @classmethod
    def tearDownClass(cls):
        """Re-enable logging after tests"""
        logging.disable(logging.NOTSET)
    
    def test_translations_for_all_supported_languages(self):
        """Test that all supported languages have translations"""
        for lang in SUPPORTED_LANGUAGES:
            self.assertIn(lang, TRANSLATIONS, 
                          f"Language {lang} is supported but has no translations")
    
    def test_check_missing_translations_fixes_gaps(self):
        """Test that check_missing_translations fixes missing translations"""
        # Create a test key in English
        test_key = "test_key_for_unit_test"
        TRANSLATIONS["en"][test_key] = "Test value"
        
        # Run the function that fixes missing translations
        check_missing_translations()
        
        # Verify the key exists in all languages
        for lang in TRANSLATIONS:
            if lang != "en":
                self.assertIn(test_key, TRANSLATIONS[lang],
                             f"Missing translation for {test_key} in {lang} not fixed")
        
        # Clean up
        for lang in TRANSLATIONS:
            if test_key in TRANSLATIONS[lang]:
                del TRANSLATIONS[lang][test_key]

    def test_get_text_with_all_languages(self):
        """Test get_text function with all supported languages"""
        key = "welcome"  # A key that should exist in all languages
        
        for lang in SUPPORTED_LANGUAGES:
            text = get_text(key, lang)
            self.assertIsNotNone(text, f"No translation for key '{key}' in {lang}")
            self.assertNotIn("[Missing", text, f"Missing translation for '{key}' in {lang}")
    
    def test_get_text_fallback_to_english(self):
        """Test that get_text falls back to English for missing translations"""
        # Use a key that definitely doesn't exist in other languages
        nonexistent_key = "nonexistent_key_for_testing_" + str(id(self))
        TRANSLATIONS["en"][nonexistent_key] = "Test English text"
        
        for lang in SUPPORTED_LANGUAGES:
            if lang != "en":
                text = get_text(nonexistent_key, lang)
                self.assertEqual(text, "Test English text", 
                                f"Fallback to English failed for {lang}")
        
        # Clean up
        del TRANSLATIONS["en"][nonexistent_key]
    
    def test_get_text_with_formatting(self):
        """Test that get_text handles formatting parameters correctly"""
        for lang in SUPPORTED_LANGUAGES:
            # Test with a key that uses formatting
            text = get_text("main_actions_status", lang, count=5)
            self.assertIn("5", text, f"Formatting failed in {lang}")
            self.assertNotIn("{count}", text, f"Formatting failed in {lang}")
    
    def test_resource_names_in_all_languages(self):
        """Test that resource names are available in all languages"""
        resources = ["influence", "resources", "information", "force"]
        
        for lang in SUPPORTED_LANGUAGES:
            for resource in resources:
                name = get_resource_name(resource, lang)
                self.assertIsNotNone(name, f"No translation for resource '{resource}' in {lang}")
                self.assertNotEqual(name, "", f"Empty translation for resource '{resource}' in {lang}")

    def test_cycle_names_in_all_languages(self):
        """Test that cycle names are available in all languages"""
        cycles = ["morning", "evening"]
        
        for lang in SUPPORTED_LANGUAGES:
            for cycle in cycles:
                name = get_cycle_name(cycle, lang)
                self.assertIsNotNone(name, f"No translation for cycle '{cycle}' in {lang}")
                self.assertNotEqual(name, "", f"Empty translation for cycle '{cycle}' in {lang}")

    def test_action_names_in_all_languages(self):
        """Test that action names are available in all languages"""
        actions = ["influence", "attack", "defense", "recon", "info", "support"]
        
        for lang in SUPPORTED_LANGUAGES:
            for action in actions:
                name = get_action_name(action, lang)
                self.assertIsNotNone(name, f"No translation for action '{action}' in {lang}")
                self.assertNotEqual(name, "", f"Empty translation for action '{action}' in {lang}")

class TestLanguageDetection(unittest.TestCase):
    """Test case for language detection feature"""
    
    @patch('language_utils.get_player_language')
    async def test_detect_user_language_from_database(self, mock_get_player_language):
        """Test detecting language from database settings"""
        mock_get_player_language.return_value = "ru"
        
        update = MagicMock()
        update.effective_user.id = 12345
        
        language = await detect_user_language(update)
        self.assertEqual(language, "ru", "Failed to detect language from database")
    
    @patch('language_utils.get_player_language')
    @patch('language_utils._update_detected_language')
    async def test_detect_user_language_from_telegram(self, mock_update_detected, mock_get_player_language):
        """Test detecting language from Telegram settings"""
        # Simulate no language in database
        mock_get_player_language.return_value = None
        
        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.language_code = "ru-RU"
        
        language = await detect_user_language(update)
        self.assertEqual(language, "ru", "Failed to detect language from Telegram")
        mock_update_detected.assert_called_once_with(12345, "ru")
    
    @patch('language_utils.get_player_language')
    async def test_detect_user_language_defaults_to_english(self, mock_get_player_language):
        """Test that detection defaults to English if no language found"""
        # Simulate no language in database
        mock_get_player_language.return_value = None
        
        update = MagicMock()
        update.effective_user.id = 12345
        update.effective_user.language_code = "fr"  # Unsupported language
        
        language = await detect_user_language(update)
        self.assertEqual(language, "en", "Failed to default to English for unsupported language")

if __name__ == '__main__':
    unittest.main() 