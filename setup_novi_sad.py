#!/usr/bin/env python3
import os
import sys
import logging
import sqlite3
import subprocess

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_db_updates():
    """Run database schema updates and populate with correct data."""
    try:
        # Run schema update
        logger.info("Running database schema updates...")
        schema_result = subprocess.run(
            [sys.executable, "db/update_schema.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(schema_result.stdout)
        
        # Populate politicians
        logger.info("Populating politicians...")
        politicians_result = subprocess.run(
            [sys.executable, "db/populate_politicians.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(politicians_result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Error running database updates: {e}")
        logger.error(f"Output: {e.stdout}\nError: {e.stderr}")
        return False

def verify_configuration():
    """Verify that the configuration is correct."""
    try:
        # Check if database exists
        if not os.path.exists('belgrade_game.db'):
            logger.error("Database file not found. Make sure to create it first.")
            return False
        
        # Connect to database
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Verify districts
        cursor.execute("SELECT COUNT(*) FROM districts")
        district_count = cursor.fetchone()[0]
        
        if district_count < 8:
            logger.warning(f"Expected at least 8 districts, but found {district_count}")
        else:
            logger.info(f"Found {district_count} districts")
        
        # Verify politicians
        cursor.execute("SELECT COUNT(*) FROM politicians WHERE is_international = 0")
        local_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM politicians WHERE is_international = 1")
        international_count = cursor.fetchone()[0]
        
        if local_count < 9:
            logger.warning(f"Expected at least 9 local politicians, but found {local_count}")
        else:
            logger.info(f"Found {local_count} local politicians")
            
        if international_count < 10:
            logger.warning(f"Expected at least 10 international politicians, but found {international_count}")
        else:
            logger.info(f"Found {international_count} international politicians")
        
        # Sample check of resources
        cursor.execute("""
        SELECT district_id, influence_resource, resources_resource, information_resource, force_resource 
        FROM districts LIMIT 5
        """)
        district_resources = cursor.fetchall()
        
        for district in district_resources:
            logger.info(f"District {district[0]}: " + 
                      f"Influence={district[1]}, Gotovina={district[2]}, " +
                      f"Information={district[3]}, Force={district[4]}")
        
        conn.close()
        return True
    except Exception as e:
        logger.error(f"Error verifying configuration: {e}")
        return False

def run_tests():
    """Run tests to verify everything works correctly."""
    try:
        # Run all tests
        logger.info("Running tests...")
        test_result = subprocess.run(
            [sys.executable, "tests/run_all_tests.py"],
            check=True,
            capture_output=True,
            text=True
        )
        logger.info(test_result.stdout)
        
        return True
    except subprocess.CalledProcessError as e:
        logger.error(f"Tests failed: {e}")
        logger.error(f"Output: {e.stdout}\nError: {e.stderr}")
        return False

def main():
    """Main function to set up the game for Novi Sad."""
    logger.info("Setting up Novi Sad game configuration...")
    
    # Run database updates
    if not run_db_updates():
        logger.error("Failed to update database schema")
        return False
    
    # Verify configuration
    if not verify_configuration():
        logger.error("Configuration verification failed")
        return False
    
    # Run tests
    if not run_tests():
        logger.error("Tests failed")
        return False
    
    logger.info("Setup complete! The game is now configured for Novi Sad, Yugoslavia.")
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1) 