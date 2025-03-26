#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Database permissions checker - utility to diagnose database access issues.
"""

import logging

from db.supabase_client import execute_sql, get_supabase

logger = logging.getLogger(__name__)

async def check_database_permissions():
    """
    Check database permissions and diagnose common issues.
    
    This function runs a series of tests to verify database connectivity, schema access,
    and function execution permissions. It logs detailed information about any issues
    found to help diagnose database-related problems.
    """
    logger.info("Starting database permission check...")
    issues_found = 0
    
    # Test 1: Basic connectivity
    try:
        logger.info("Testing basic database connectivity...")
        client = get_supabase()
        response = client.table("game.players").select("count", "exact").limit(1).execute()
        logger.info("✓ Basic connectivity test passed")
    except Exception as e:
        logger.error(f"✗ Basic connectivity test failed: {e}")
        issues_found += 1
        
    # Test 2: Schema existence
    try:
        logger.info("Checking if 'game' schema exists...")
        result = await execute_sql(
            "SELECT EXISTS (SELECT 1 FROM information_schema.schemata WHERE schema_name = 'game');"
        )
        
        if result and isinstance(result, list) and len(result) > 0:
            schema_exists = result[0].get('exists', False)
            if schema_exists:
                logger.info("✓ 'game' schema exists")
            else:
                logger.error("✗ 'game' schema does not exist")
                issues_found += 1
        else:
            logger.error("✗ Could not verify schema existence")
            issues_found += 1
    except Exception as e:
        logger.error(f"✗ Schema check failed: {e}")
        issues_found += 1
    
    # Test 3: Table access
    try:
        logger.info("Testing access to players table...")
        result = await execute_sql("SELECT COUNT(*) FROM game.players;")
        if result:
            logger.info(f"✓ Players table access successful: {result}")
        else:
            logger.warning("⚠ Players table access test returned no result")
            issues_found += 1
    except Exception as e:
        logger.error(f"✗ Players table access failed: {e}")
        issues_found += 1
        
    # Test 4: Function existence and access
    try:
        logger.info("Testing RPC function access...")
        client = get_supabase()
        
        # Try player_exists function without schema prefix
        try:
            response = client.rpc("player_exists", {"p_telegram_id": "test"}).execute()
            logger.info("✓ Function 'player_exists' exists and is accessible")
        except Exception as e:
            logger.warning(f"⚠ Function 'player_exists' test failed: {e}")
            issues_found += 1
            
            # Try alternative function naming
            try:
                response = client.rpc("game_player_exists", {"p_telegram_id": "test"}).execute()
                logger.info("✓ Function 'game_player_exists' exists and is accessible")
                logger.info("ℹ Important: Use 'game_player_exists' instead of 'player_exists'")
            except Exception as e2:
                logger.error(f"✗ Alternative function test failed: {e2}")
                issues_found += 1
                
    except Exception as e:
        logger.error(f"✗ Function access test failed: {e}")
        issues_found += 1
    
    # Report overall status
    if issues_found == 0:
        logger.info("✓ All database permission checks passed. No issues detected.")
    else:
        logger.warning(f"⚠ Found {issues_found} potential database access issues.")
        logger.info("""
Database access troubleshooting recommendations:
1. Check that Supabase credentials (URL and API key) are correct
2. Ensure the database schema 'game' exists and has been properly initialized
3. Verify that your Supabase API key has the necessary permissions
4. Check that RLS (Row Level Security) policies are properly configured
5. For function-related errors, ensure functions are created without schema in their names for RPC calls
        """)
    
    return issues_found
