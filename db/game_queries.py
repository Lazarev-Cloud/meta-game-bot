"""
Game-specific database queries and operations.
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from .queries import db_connection_pool, db_transaction

logger = logging.getLogger(__name__)

@db_transaction
def get_district_info(conn, district_id: str) -> Optional[Dict[str, Any]]:
    """Get district information."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.*, 
               COALESCE(dc.control_points, 0) as control_points,
               COALESCE(p.character_name, '') as controller_name
        FROM districts d
        LEFT JOIN district_control dc ON d.district_id = dc.district_id
        LEFT JOIN players p ON dc.player_id = p.player_id
        WHERE d.district_id = ?
    """, (district_id,))
    result = cursor.fetchone()
    if not result:
        return None
    
    return {
        'district_id': result[0],
        'name': result[1],
        'description': result[2],
        'influence_resource': result[3],
        'resources_resource': result[4],
        'information_resource': result[5],
        'force_resource': result[6],
        'control_points': result[7],
        'controller_name': result[8]
    }

@db_transaction
def get_politician_info(conn, politician_id: int) -> Optional[Dict[str, Any]]:
    """Get politician information."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, d.name as district_name
        FROM politicians p
        LEFT JOIN districts d ON p.district_id = d.district_id
        WHERE p.politician_id = ?
    """, (politician_id,))
    result = cursor.fetchone()
    if not result:
        return None
    
    return {
        'politician_id': result[0],
        'name': result[1],
        'role': result[2],
        'ideology_score': result[3],
        'district_id': result[4],
        'influence': result[5],
        'friendliness': result[6],
        'is_international': result[7],
        'description': result[8],
        'district_name': result[9]
    }

@db_transaction
def get_all_districts(conn) -> List[Tuple[str, str]]:
    """Get all districts."""
    cursor = conn.cursor()
    cursor.execute("SELECT district_id, name FROM districts ORDER BY name")
    return cursor.fetchall()

@db_transaction
def get_all_politicians(conn, is_international: bool = False) -> List[Dict[str, Any]]:
    """Get all politicians."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, d.name as district_name
        FROM politicians p
        LEFT JOIN districts d ON p.district_id = d.district_id
        WHERE p.is_international = ?
        ORDER BY p.name
    """, (1 if is_international else 0,))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'politician_id': row[0],
            'name': row[1],
            'role': row[2],
            'ideology_score': row[3],
            'district_id': row[4],
            'influence': row[5],
            'friendliness': row[6],
            'is_international': row[7],
            'description': row[8],
            'district_name': row[9]
        })
    return results

@db_transaction
def get_player_districts(conn, player_id: int) -> List[Dict[str, Any]]:
    """Get districts controlled by a player."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT d.district_id, d.name, dc.control_points 
        FROM district_control dc
        JOIN districts d ON dc.district_id = d.district_id
        WHERE dc.player_id = ?
        ORDER BY dc.control_points DESC
    """, (player_id,))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'district_id': row[0],
            'name': row[1],
            'control_points': row[2]
        })
    return results

@db_transaction
def get_player_politicians(conn, player_id: int) -> List[Dict[str, Any]]:
    """Get politicians with relationships to a player."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT p.*, pr.friendliness, pr.interaction_count, d.name as district_name
        FROM politicians p
        LEFT JOIN politician_relationships pr ON p.politician_id = pr.politician_id AND pr.player_id = ?
        LEFT JOIN districts d ON p.district_id = d.district_id
        ORDER BY COALESCE(pr.friendliness, 50) DESC
    """, (player_id,))
    
    results = []
    for row in cursor.fetchall():
        results.append({
            'politician_id': row[0],
            'name': row[1],
            'role': row[2],
            'ideology_score': row[3],
            'district_id': row[4],
            'influence': row[5],
            'friendliness': row[10] if row[10] is not None else 50,
            'interaction_count': row[11] if row[11] is not None else 0,
            'district_name': row[12]
        })
    return results

@db_transaction
def get_player_resources(conn, player_id: int) -> Dict[str, int]:
    """Get player resources."""
    cursor = conn.cursor()
    cursor.execute("""
        SELECT influence, resources, information, force
        FROM resources
        WHERE player_id = ?
    """, (player_id,))

    row = cursor.fetchone()
    if not row:
        return {"influence": 0, "resources": 0, "information": 0, "force": 0}

    return {
        "influence": row[0],
        "resources": row[1],
        "information": row[2],
        "force": row[3]
    }

@db_transaction
def update_district_control(conn, player_id: int, district_id: str, points: int) -> bool:
    """Update district control points."""
    cursor = conn.cursor()

    # Check current control
    cursor.execute("""
        SELECT control_points
        FROM district_control
        WHERE player_id = ? AND district_id = ?
    """, (player_id, district_id))

    row = cursor.fetchone()

    if row:
        # Update existing control
        new_points = max(0, row[0] + points)
        cursor.execute("""
            UPDATE district_control
            SET control_points = ?
            WHERE player_id = ? AND district_id = ?
        """, (new_points, player_id, district_id))
    else:
        # Insert new control record
        cursor.execute("""
            INSERT INTO district_control (player_id, district_id, control_points)
            VALUES (?, ?, ?)
        """, (player_id, district_id, max(0, points)))

    return True