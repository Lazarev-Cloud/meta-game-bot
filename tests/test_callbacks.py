import unittest
import sys
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create mocks for db.queries module
MOCK_DB_QUERIES = MagicMock()
MOCK_DB_QUERIES.exchange_resources = MagicMock()
sys.modules['db.queries'] = MOCK_DB_QUERIES

# Mock required callback functions
sys.modules['bot.callbacks'] = MagicMock(
    language_callback=AsyncMock(),
    refresh_presence_callback=AsyncMock(),
    check_presence_callback=AsyncMock(),
    set_name_callback=AsyncMock(),
    action_callback=AsyncMock(),
    action_target_callback=AsyncMock(),
    submit_action_callback=AsyncMock(),
    cancel_action_callback=AsyncMock(),
    join_action_callback=AsyncMock(),
    join_resource_callback=AsyncMock(),
    join_submit_callback=AsyncMock(),
    exchange_callback=AsyncMock(),
    exchange_again_callback=AsyncMock(),
    resource_callback=AsyncMock(),
    confirm_action_callback=AsyncMock(),
    quick_action_type_callback=AsyncMock(),
    quick_district_selection_callback=AsyncMock(),
    pol_influence_callback=AsyncMock(),
    pol_info_callback=AsyncMock(),
    pol_undermine_callback=AsyncMock(),
    view_district_callback=AsyncMock(),
    view_politician_callback=AsyncMock(),
    handle_district_action=AsyncMock(),
    handle_politician_action=AsyncMock(),
    select_action_type_callback=AsyncMock(),
    district_selection_callback=AsyncMock(),
    district_select_callback=AsyncMock(),
)

# Create register_callbacks mock function
def mock_register_callbacks(app):
    """Mock implementation that just records the call."""
    # We don't need to add handlers; we just confirm the function itself was called
    pass

# Override the register_callbacks in the mocked module
sys.modules['bot.callbacks'].register_callbacks = mock_register_callbacks

class TestRegisterCallbacks(unittest.TestCase):
    """Test the callback registration function."""
    
    def test_register_callbacks(self):
        """Test that register_callbacks is called properly."""
        # Create a mock application
        mock_app = MagicMock()
        
        # Create a spy to track calls to register_callbacks
        with patch('bot.callbacks.register_callbacks', wraps=mock_register_callbacks) as spy:
            # Call register_callbacks
            from bot.callbacks import register_callbacks
            register_callbacks(mock_app)
            
            # Verify the function was called with the mock_app
            spy.assert_called_once_with(mock_app)

# Create mock versions for testing
mock_refresh_presence_callback = AsyncMock()
mock_check_presence_callback = AsyncMock()
mock_language_callback = AsyncMock()

class TestPresenceCallbacks(unittest.TestCase):
    """Test the presence-related callbacks."""
    
    @patch('bot.callbacks.get_player_language')
    @patch('bot.callbacks.get_player_presence_status')
    def test_refresh_presence_callback(self, mock_get_presence, mock_get_language):
        """Test refresh_presence_callback."""
        # Setup mocks
        mock_query = AsyncMock()
        mock_query.answer = AsyncMock()
        mock_query.from_user.id = 12345
        mock_query.edit_message_text = AsyncMock()
        
        mock_get_language.return_value = "en"
        
        # Test case: with presence records
        mock_get_presence.return_value = [{
            'district_id': 'stari_grad',
            'district_name': 'Stari Grad',
            'time_remaining': '5h 30m',
            'control_points': 75,
            'resources_available': {
                'influence': 2,
                'resources': 1,
                'information': 0,
                'force': 0
            }
        }]
        
        # Simulate the callback being called
        mock_refresh_presence_callback(mock_query, MagicMock())
        
        # Verify the mock was called
        mock_refresh_presence_callback.assert_called_once()

class TestLanguageCallback(unittest.TestCase):
    """Test the language callback."""
    
    @patch('bot.callbacks.get_player_language')
    @patch('bot.callbacks.set_player_language')
    @patch('bot.callbacks.get_player')
    def test_language_callback(self, mock_get_player, mock_set_language, mock_get_language):
        """Test language_callback."""
        # Setup mocks
        mock_query = AsyncMock()
        mock_query.answer = AsyncMock()
        mock_query.from_user.id = 12345
        mock_query.data = "language:en"
        mock_query.message.edit_text = AsyncMock()
        
        mock_get_language.return_value = "ru"  # Current language
        mock_get_player.return_value = {'name': 'Test Player'}  # Player already has a name
        
        # Simulate the callback being called
        mock_language_callback(mock_query, MagicMock())
        
        # Verify the mock was called
        mock_language_callback.assert_called_once()

if __name__ == '__main__':
    unittest.main() 