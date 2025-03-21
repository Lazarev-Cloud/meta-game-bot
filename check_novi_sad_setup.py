#!/usr/bin/env python3
import sqlite3
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def check_setup():
    """Verify that the Novi Sad game setup is complete."""
    conn = None
    try:
        # Connect to the database
        print("Connecting to database...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check districts
        print("\n=== Checking Districts ===")
        cursor.execute("SELECT COUNT(*) FROM districts")
        district_count = cursor.fetchone()[0]
        
        if district_count >= 8:
            print(f"✅ Found {district_count} districts")
            
            # Check district resources
            cursor.execute("""
            SELECT district_id, name, influence_resource, resources_resource, 
                   information_resource, force_resource 
            FROM districts
            """)
            districts = cursor.fetchall()
            
            print("\nDistrict Resources:")
            for district in districts:
                district_id, name, influence, gotovina, info, force = district
                print(f"- {name}: Influence={influence}, Gotovina={gotovina}, Information={info}, Force={force}")
        else:
            print(f"❌ Expected at least 8 districts, but found {district_count}")
        
        # Check politicians
        print("\n=== Checking Politicians ===")
        
        # Local politicians
        cursor.execute("SELECT COUNT(*) FROM politicians WHERE is_international = 0")
        local_count = cursor.fetchone()[0]
        
        if local_count >= 9:
            print(f"✅ Found {local_count} local politicians")
            
            # Sample local politicians
            cursor.execute("""
            SELECT name, role, district_id, ideology_score
            FROM politicians
            WHERE is_international = 0
            LIMIT 5
            """)
            locals = cursor.fetchall()
            
            print("\nSample Local Politicians:")
            for politician in locals:
                name, role, district, ideology = politician
                print(f"- {name} ({role}): District={district}, Ideology={ideology}")
        else:
            print(f"❌ Expected at least 9 local politicians, but found {local_count}")
        
        # International politicians
        cursor.execute("SELECT COUNT(*) FROM politicians WHERE is_international = 1")
        intl_count = cursor.fetchone()[0]
        
        if intl_count >= 10:
            print(f"✅ Found {intl_count} international politicians")
            
            # Sample international politicians
            cursor.execute("""
            SELECT name, role, ideology_score
            FROM politicians
            WHERE is_international = 1
            LIMIT 5
            """)
            internationals = cursor.fetchall()
            
            print("\nSample International Politicians:")
            for politician in internationals:
                name, country, ideology = politician
                print(f"- {name} ({country}): Ideology={ideology}")
        else:
            print(f"❌ Expected at least 10 international politicians, but found {intl_count}")
        
        # Check if any districts are referenced by politicians that don't exist
        cursor.execute("""
        SELECT p.politician_id, p.name, p.district_id
        FROM politicians p
        LEFT JOIN districts d ON p.district_id = d.district_id
        WHERE p.district_id IS NOT NULL AND d.district_id IS NULL
        """)
        invalid_districts = cursor.fetchall()
        
        if invalid_districts:
            print("\n❌ Found politicians with invalid district references:")
            for politician in invalid_districts:
                pol_id, name, district_id = politician
                print(f"- {name} references non-existent district: {district_id}")
        else:
            print("\n✅ All politician district references are valid")
        
        # Check translation keys
        # Get district_ids from database
        cursor.execute("SELECT district_id FROM districts")
        district_ids = [row[0] for row in cursor.fetchall()]
        
        # Get politician_ids from database
        cursor.execute("SELECT politician_id FROM politicians")
        politician_ids = [row[0] for row in cursor.fetchall()]
        
        # Check welcome message translation
        try:
            from languages import get_text
            
            welcome_en = get_text("welcome", "en")
            welcome_ru = get_text("welcome", "ru")
            welcome_sr = get_text("welcome", "sr")
            
            print("\n=== Checking Translations ===")
            if "Novi Sad" in welcome_en:
                print("✅ English welcome message references Novi Sad")
            else:
                print("❌ English welcome message doesn't reference Novi Sad")
                
            if "Нови-Сад" in welcome_ru or "Нови Сад" in welcome_ru:
                print("✅ Russian welcome message references Novi Sad")
            else:
                print("❌ Russian welcome message doesn't reference Novi Sad")
                
            if "Нови Сад" in welcome_sr:
                print("✅ Serbian welcome message references Novi Sad")
            else:
                print("❌ Serbian welcome message doesn't reference Novi Sad")
        except:
            print("❌ Couldn't check translations (import error)")
        
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    print("Checking Novi Sad game setup...")
    success = check_setup()
    if success:
        print("\n✅ Novi Sad game setup verification completed")
    else:
        print("\n❌ Failed to verify Novi Sad game setup")
        
    sys.exit(0 if success else 1) 