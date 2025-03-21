#!/usr/bin/env python3
"""
Test runner script to execute all tests in the tests directory.
"""
import unittest
import sys
import os

def run_all_tests():
    """Discover and run all tests in the tests directory."""
    # Get the directory containing this file
    test_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Discover tests in the directory
    test_suite = unittest.defaultTestLoader.discover(test_dir)
    
    # Create a test runner
    test_runner = unittest.TextTestRunner(verbosity=2)
    
    # Run the tests
    result = test_runner.run(test_suite)
    
    # Return proper exit code
    return 0 if result.wasSuccessful() else 1

if __name__ == '__main__':
    # Add parent directory to path to allow importing modules
    parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    sys.path.insert(0, parent_dir)
    
    # Run tests and exit with appropriate code
    sys.exit(run_all_tests()) 