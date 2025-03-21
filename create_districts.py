#!/usr/bin/env python3
import sqlite3
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def setup_districts():
    """Create and populate districts table with Belgrade districts."""
    conn = None
    try:
        # Connect to the database
        print("Connecting to database...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if districts table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='districts'")
        if cursor.fetchone():
            # Drop existing districts table if it exists
            print("Dropping existing districts table...")
            cursor.execute("DROP TABLE IF EXISTS districts")
        
        # Create a fresh districts table
        print("Creating new districts table...")
        cursor.execute('''
        CREATE TABLE districts (
            district_id TEXT PRIMARY KEY,
            name TEXT,
            description TEXT,
            influence_resource INTEGER DEFAULT 0,
            resources_resource INTEGER DEFAULT 0,
            information_resource INTEGER DEFAULT 0,
            force_resource INTEGER DEFAULT 0
        )
        ''')
        
        # Districts data based on Belgrade game rules
        districts = [
            # district_id, name, description, influence, gotovina, information, force
            ('stari_grad', 'Stari Grad', 'Historical and administrative center', 2, 0, 2, 0),
            ('novi_beograd', 'Novi Beograd', 'Business center and modern developments', 1, 3, 0, 0),
            ('zemun', 'Zemun', 'Historical district with industrial areas', 0, 2, 2, 0),
            ('savski_venac', 'Savski Venac', 'Government institutions and embassies', 3, 0, 1, 0),
            ('vozdovac', 'Voždovac', 'Military installations and security', 1, 0, 0, 3),
            ('cukarica', 'Čukarica', 'Industrial zone and working class', 0, 4, 0, 0),
            ('palilula', 'Palilula', 'University areas and hospitals', 0, 0, 3, 1),
            ('vracar', 'Vračar', 'Cultural and media center', 2, 0, 2, 0)
        ]
        
        # Insert districts
        print(f"Adding {len(districts)} districts...")
        for district in districts:
            print(f"Adding district: {district[1]}")
            cursor.execute('''
            INSERT INTO districts 
            (district_id, name, description, influence_resource, resources_resource, information_resource, force_resource) 
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', district)
        
        # Commit changes
        conn.commit()
        
        # Verify the data was inserted
        cursor.execute("SELECT COUNT(*) FROM districts")
        district_count = cursor.fetchone()[0]
        
        print(f"Successfully added {district_count} districts")
        
        # Show some sample data
        cursor.execute("SELECT district_id, name, influence_resource, resources_resource, information_resource, force_resource FROM districts LIMIT 5")
        print("\nSample districts data:")
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, Name: {row[1]}, Resources: Influence={row[2]}, Gotovina={row[3]}, Information={row[4]}, Force={row[5]}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    print("Starting district setup for Belgrade game...")
    success = setup_districts()
    if success:
        print("✅ Successfully set up districts for Belgrade game")
    else:
        print("❌ Failed to set up districts")
        
    sys.exit(0 if success else 1) 