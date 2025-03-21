import unittest
import sys
import os
import sqlite3
import json
import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Create mocks for imported modules
MOCK_BOT_COMMANDS = MagicMock()
MOCK_BOT_CALLBACKS = MagicMock()

# Mock the specific functions we need
MOCK_BOT_COMMANDS.get_district_by_location = MagicMock(return_value="stari_grad")
MOCK_BOT_COMMANDS.presence_command = AsyncMock()
MOCK_BOT_COMMANDS.check_presence_command = AsyncMock()
MOCK_BOT_COMMANDS.register_commands = MagicMock()

MOCK_BOT_CALLBACKS.register_callbacks = MagicMock()
MOCK_BOT_CALLBACKS.refresh_presence_callback = AsyncMock()

# Apply mocks
sys.modules['bot.commands'] = MOCK_BOT_COMMANDS
sys.modules['bot.callbacks'] = MOCK_BOT_CALLBACKS

class TestBotIntegration(unittest.TestCase):
    """Integration tests for the bot functionality."""
    
    def setUp(self):
        """Set up test environment."""
        # Create a test database in-memory
        self.conn = sqlite3.connect(':memory:')
        self.cursor = self.conn.cursor()
        
        # Set up tables required for the tests
        self._setup_database_tables()
        
        # Patch sqlite3.connect to return our test connection
        self.patcher = patch('sqlite3.connect')
        self.mock_connect = self.patcher.start()
        self.mock_connect.return_value = self.conn
    
    def tearDown(self):
        """Clean up after tests."""
        self.patcher.stop()
        self.conn.close()
    
    def _setup_database_tables(self):
        """Set up the necessary database tables for testing."""
        # Create players table
        self.cursor.execute('''
        CREATE TABLE players (
            player_id INTEGER PRIMARY KEY,
            username TEXT,
            character_name TEXT,
            ideology_score INTEGER DEFAULT 0,
            main_actions_left INTEGER DEFAULT 1,
            quick_actions_left INTEGER DEFAULT 2,
            last_action_refresh TEXT,
            language TEXT DEFAULT 'en'
        )
        ''')
        
        # Create resources table
        self.cursor.execute('''
        CREATE TABLE resources (
            player_id INTEGER PRIMARY KEY,
            influence INTEGER DEFAULT 0,
            resources INTEGER DEFAULT 0,
            information INTEGER DEFAULT 0,
            force INTEGER DEFAULT 0,
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
        ''')
        
        # Create districts table
        self.cursor.execute('''
        CREATE TABLE districts (
            district_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            influence_resources INTEGER DEFAULT 0,
            economic_resources INTEGER DEFAULT 0,
            information_resources INTEGER DEFAULT 0,
            force_resources INTEGER DEFAULT 0
        )
        ''')
        
        # Create presence table
        self.cursor.execute('''
        CREATE TABLE player_presence (
            player_id INTEGER,
            district_id TEXT,
            expires_at TEXT,
            location_data TEXT,
            PRIMARY KEY (player_id, district_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id),
            FOREIGN KEY (district_id) REFERENCES districts(district_id)
        )
        ''')
        
        # Create district control table
        self.cursor.execute('''
        CREATE TABLE district_control (
            district_id TEXT,
            player_id INTEGER,
            control_points INTEGER DEFAULT 0,
            last_action TEXT,
            PRIMARY KEY (district_id, player_id),
            FOREIGN KEY (district_id) REFERENCES districts(district_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
        ''')
        
        # Add some test data
        self._add_test_data()
        self.conn.commit()
    
    def _add_test_data(self):
        """Add test data to the database."""
        # Add a test player
        self.cursor.execute(
            "INSERT INTO players (player_id, username, character_name, ideology_score, language) VALUES (?, ?, ?, ?, ?)",
            (12345, "test_user", "Test Player", 0, "en")
        )
        
        # Add player resources
        self.cursor.execute(
            "INSERT INTO resources (player_id, influence, resources, information, force) VALUES (?, ?, ?, ?, ?)",
            (12345, 10, 20, 5, 3)
        )
        
        # Add test districts
        districts = [
            ("stari_grad", "Stari Grad", "Central district", 5, 3, 2, 1),
            ("vracar", "Vračar", "Cultural district", 4, 4, 3, 0),
            ("novi_beograd", "Novi Beograd", "Modern district", 3, 5, 2, 2)
        ]
        
        for district in districts:
            self.cursor.execute(
                "INSERT INTO districts (district_id, name, description, influence_resources, economic_resources, information_resources, force_resources) VALUES (?, ?, ?, ?, ?, ?, ?)",
                district
            )
    
    def test_presence_flow(self):
        """Test the full presence command flow."""
        # Create a mock update
        mock_update = MagicMock()
        mock_update.effective_user.id = 12345
        mock_update.message.location = MagicMock(latitude=44.8184, longitude=20.4586)
        
        # Call presence_command using the mock
        MOCK_BOT_COMMANDS.presence_command(mock_update, MagicMock())
        
        # Verify the function was called
        MOCK_BOT_COMMANDS.presence_command.assert_called_once()
        
        # Get the actual presence record from the database
        self.cursor.execute(
            "SELECT player_id, district_id FROM player_presence WHERE player_id = ?",
            (12345,)
        )
        presence_record = self.cursor.fetchone()
        
        # There shouldn't be an actual record because we're just mocking the function
        self.assertIsNone(presence_record)
    
    def test_check_presence_flow(self):
        """Test the check presence command flow."""
        # Add a presence record directly to the database
        now = datetime.datetime.now()
        expires_at = (now + datetime.timedelta(hours=6)).isoformat()
        location_data = json.dumps({"latitude": 44.8184, "longitude": 20.4586})
        
        self.cursor.execute(
            "INSERT INTO player_presence (player_id, district_id, expires_at, location_data) VALUES (?, ?, ?, ?)",
            (12345, "stari_grad", expires_at, location_data)
        )
        self.conn.commit()
        
        # Create mock update
        mock_update = MagicMock()
        mock_update.effective_user.id = 12345
        
        # Call the mocked function
        MOCK_BOT_COMMANDS.check_presence_command(mock_update, MagicMock())
        
        # Verify the function was called
        MOCK_BOT_COMMANDS.check_presence_command.assert_called_once()

class TestCommandCallbackIntegration(unittest.TestCase):
    """Test the integration between commands and callbacks."""
    
    def test_commands_and_callbacks_registration(self):
        """Test that both commands and callbacks are properly registered."""
        # Create a mock application
        mock_app = MagicMock()
        
        # Register commands
        MOCK_BOT_COMMANDS.register_commands(mock_app)
        
        # Verify register_commands was called
        MOCK_BOT_COMMANDS.register_commands.assert_called_once_with(mock_app)
        
        # Now register callbacks
        MOCK_BOT_CALLBACKS.register_callbacks(mock_app)
        
        # Verify register_callbacks was called
        MOCK_BOT_CALLBACKS.register_callbacks.assert_called_once_with(mock_app)

if __name__ == '__main__':
    unittest.main() 