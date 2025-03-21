#!/usr/bin/env python3
import sqlite3
import sys
import logging

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def setup_politicians():
    """Create and populate politicians table with Novi Sad politicians."""
    conn = None
    try:
        # Connect to the database
        print("Connecting to database...")
        conn = sqlite3.connect('novi_sad_game.db')
        cursor = conn.cursor()
        
        # Check if politicians table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='politicians'")
        if cursor.fetchone():
            # Drop existing politicians table if it exists
            print("Dropping existing politicians table...")
            cursor.execute("DROP TABLE IF EXISTS politicians")
        
        # Create a fresh politicians table
        print("Creating new politicians table...")
        cursor.execute('''
        CREATE TABLE politicians (
            politician_id TEXT PRIMARY KEY,
            name TEXT,
            role TEXT,
            description TEXT,
            ideology_score INTEGER,
            district_id TEXT,
            influence INTEGER DEFAULT 0,
            is_international INTEGER DEFAULT 0,
            FOREIGN KEY (district_id) REFERENCES districts(district_id)
        )
        ''')
        
        # Drop the friendliness table if it exists
        cursor.execute("DROP TABLE IF EXISTS politician_friendliness")
        
        # Create friendliness table
        print("Creating politician_friendliness table...")
        cursor.execute('''
        CREATE TABLE politician_friendliness (
            politician_id TEXT,
            player_id INTEGER,
            friendliness INTEGER DEFAULT 0,
            PRIMARY KEY (politician_id, player_id),
            FOREIGN KEY (politician_id) REFERENCES politicians(politician_id),
            FOREIGN KEY (player_id) REFERENCES players(player_id)
        )
        ''')
        
        # Local politicians
        local_politicians = [
            ('nemanja_kovacevic', 'Nemanja Kovačević', 'Head of Belgrade City Administration',
             'Loyal to the Milošević regime, opponent of radical changes, controls city administrative resources',
             5, 'stari_grad', 6),
            
            ('miroslav_vasilevic', 'Miroslav Vasiljević', 'Deputy Head of Administration',
             'Can slow down reforms, but helps with bureaucracy',
             3, 'stari_grad', 4),
            
            ('dragan_jovic', 'Professor Dragan Jović', 'Rector of Belgrade University',
             'Intellectual, supporter of democratization and European integration, influential among students and intelligentsia',
             -5, 'vracar', 7),
            
            ('zoran_markovic', 'Zoran Marković', 'Director of Belgrade Security Services',
             'Security hardliner, coordinates police and security apparatus, loyal to the regime',
             3, 'palilula', 5),
            
            ('stefan_nikolic', 'Father Stefan Nikolić', 'Orthodox priest at St. Sava Church',
             'Religious figure with moderate influence in the city, has connections with politicians and business leaders',
             2, 'vracar', 4),
            
            ('branko_petrovic', 'Colonel Branko Petrović', 'Commander of the Belgrade military garrison',
             'Military with traditionalist views, loyal to the regime and ready for decisive measures',
             4, 'vozdovac', 6),
            
            ('goran_radic', 'Goran Radić', 'Leader of the Machine Builders Union',
             'Represents workers interests, criticizes economic policy but takes a moderate position',
             -2, 'cukarica', 4),
            
            ('maria_kovac', 'Maria Kovač', 'Leader of the student movement "Otpor"',
             'Charismatic leader of youth protest, demands democratization and change of power',
             -4, 'novi_beograd', 5),
            
            ('bishop_irinej', 'Bishop Irinej', 'Head of the Orthodox Diocese in Belgrade',
             'Supports traditional values but advocates for peace and harmony, against violence',
             1, 'zemun', 5)
        ]
        
        # International politicians
        international_politicians = [
            ('bill_clinton', 'Bill Clinton', 'USA',
             'Strongly supports reform and democratization movements in Yugoslavia',
             -5, None, 0),
            
            ('tony_blair', 'Tony Blair', 'United Kingdom',
             'Supports economic reforms and sanctions against the regime',
             -4, None, 0),
            
            ('jacques_chirac', 'Jacques Chirac', 'France',
             'Provides diplomatic channels for all sides',
             -3, None, 0),
            
            ('joschka_fischer', 'Joschka Fischer', 'Germany',
             'Supports democratic activists',
             -2, None, 0),
            
            ('javier_solana', 'Javier Solana', 'NATO',
             'Threatens military action against the regime',
             -3, None, 0),
            
            ('zhirinovsky', 'Vladimir Zhirinovsky', 'Russia',
             'Supports destabilization, creating chaos in protest districts',
             4, None, 0),
            
            ('primakov', 'Yevgeny Primakov', 'Russia',
             'Provides diplomatic support to resist sanctions',
             2, None, 0),
            
            ('milosevic', 'Slobodan Milošević', 'Yugoslavia',
             'Uses international connections to pressure opponents',
             5, None, 0),
            
            ('havel', 'Václav Havel', 'Czech Republic',
             'Supports NGOs working for reform',
             -5, None, 0),
            
            ('albright', 'Madeleine Albright', 'USA',
             'Pushes for tougher sanctions against the regime',
             -4, None, 0)
        ]
        
        # Insert local politicians
        print(f"Adding {len(local_politicians)} local politicians...")
        for politician in local_politicians:
            print(f"Adding local politician: {politician[1]}")
            cursor.execute('''
            INSERT INTO politicians 
            (politician_id, name, role, description, ideology_score, district_id, influence, is_international) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 0)
            ''', politician)
        
        # Insert international politicians
        print(f"Adding {len(international_politicians)} international politicians...")
        for politician in international_politicians:
            print(f"Adding international politician: {politician[1]} ({politician[2]})")
            cursor.execute('''
            INSERT INTO politicians 
            (politician_id, name, role, description, ideology_score, district_id, influence, is_international) 
            VALUES (?, ?, ?, ?, ?, ?, ?, 1)
            ''', politician)
        
        # Commit changes
        conn.commit()
        
        # Verify the data was inserted
        cursor.execute("SELECT COUNT(*) FROM politicians WHERE is_international = 0")
        local_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM politicians WHERE is_international = 1")
        intl_count = cursor.fetchone()[0]
        
        print(f"Successfully added {local_count} local and {intl_count} international politicians")
        
        # Show some sample data
        cursor.execute("SELECT politician_id, name, district_id, ideology_score FROM politicians LIMIT 5")
        print("\nSample politicians data:")
        for row in cursor.fetchall():
            print(f"ID: {row[0]}, Name: {row[1]}, District: {row[2]}, Ideology: {row[3]}")
        
        conn.close()
        return True
    except Exception as e:
        print(f"ERROR: {e}")
        if conn:
            conn.close()
        return False

if __name__ == "__main__":
    print("Starting politician setup for Novi Sad game...")
    success = setup_politicians()
    if success:
        print("✅ Successfully set up politicians for Novi Sad game")
    else:
        print("❌ Failed to set up politicians")
        
    sys.exit(0 if success else 1) 