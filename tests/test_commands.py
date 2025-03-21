import unittest
import sys
import os
import sqlite3
import datetime
from unittest.mock import patch, MagicMock, AsyncMock

# Add the parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from bot.commands import (
    get_district_by_location,
    get_resource_indicator
)

class TestGetDistrictByLocation(unittest.TestCase):
    """Test the get_district_by_location function."""
    
    def test_invalid_location_data(self):
        """Test handling of invalid location data."""
        # Test with None
        result = get_district_by_location(None)
        self.assertIsNone(result)
        
        # Test with empty dict
        result = get_district_by_location({})
        self.assertIsNone(result)
        
        # Test with incomplete data
        result = get_district_by_location({"latitude": 44.8184})
        self.assertIsNone(result)
        result = get_district_by_location({"longitude": 20.4586})
        self.assertIsNone(result)
    
    def test_location_in_district(self):
        """Test location within a district boundary."""
        # Test location in Stari Grad (Novi Sad)
        location_data = {"latitude": 45.2551, "longitude": 19.8426}
        result = get_district_by_location(location_data)
        self.assertEqual(result, "stari_grad")
        
        # Test location in Liman
        location_data = {"latitude": 45.2415, "longitude": 19.8339}
        result = get_district_by_location(location_data)
        self.assertEqual(result, "liman")
    
    def test_location_outside_districts(self):
        """Test location outside all district boundaries but still within reasonable range."""
        # A location that's outside specific boundaries but close enough to return the nearest district
        location_data = {"latitude": 45.2651, "longitude": 19.8300}  # Near Detelinara
        result = get_district_by_location(location_data)
        self.assertEqual(result, "detelinara")
    
    def test_location_too_far(self):
        """Test location too far from any district."""
        # A location that's very far from Novi Sad
        location_data = {"latitude": 45.5, "longitude": 19.5}
        result = get_district_by_location(location_data)
        self.assertIsNone(result)

class TestGetResourceIndicator(unittest.TestCase):
    """Test the get_resource_indicator function."""
    
    def test_low_resources(self):
        """Test indicator for low resources."""
        self.assertEqual(get_resource_indicator(0), "🔴")
        self.assertEqual(get_resource_indicator(4), "🔴")
    
    def test_medium_resources(self):
        """Test indicator for medium resources."""
        self.assertEqual(get_resource_indicator(5), "🟡")
        self.assertEqual(get_resource_indicator(9), "🟡")
    
    def test_high_resources(self):
        """Test indicator for high resources."""
        self.assertEqual(get_resource_indicator(10), "🟢")
        self.assertEqual(get_resource_indicator(100), "🟢")

if __name__ == '__main__':
    unittest.main() 