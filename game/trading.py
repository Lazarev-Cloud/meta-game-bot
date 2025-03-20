"""
Trading system for Belgrade Game Bot
Handles creating, accepting, and managing trade offers
"""

import logging
import datetime
import json
from typing import Dict, List, Optional, Any, Tuple
from db.queries import db_connection_pool, db_transaction
from languages import get_text

logger = logging.getLogger(__name__)

# Remove the circular imports - don't import functions from db.game_queries that are defined here
# Instead only import what's actually defined there
from db.game_queries import get_player_resources


@db_transaction
def create_trade_offer(conn, sender_id: int, receiver_id: int, offer: Dict[str, int], request: Dict[str, int]) -> int:
    """
    Create a new trade offer.

    Args:
        conn: Database connection
        sender_id: ID of player making the offer
        receiver_id: ID of player receiving the offer
        offer: Dict of resources being offered {resource_type: amount}
        request: Dict of resources being requested {resource_type: amount}

    Returns:
        offer_id of created offer, or 0 if failed
    """
    try:
        cursor = conn.cursor()

        # Validate offer and request
        valid_resources = {"influence", "resources", "information", "force"}
        for resource_type in offer.keys():
            if resource_type not in valid_resources:
                logger.error(f"Invalid resource type in offer: {resource_type}")
                return 0

        for resource_type in request.keys():
            if resource_type not in valid_resources:
                logger.error(f"Invalid resource type in request: {resource_type}")
                return 0

        # Verify sender has sufficient resources
        cursor.execute(
            """
            SELECT influence, resources, information, force
            FROM resources
            WHERE player_id = ?
            """,
            (sender_id,)
        )
        sender_res = cursor.fetchone()
        if not sender_res:
            return 0

        sender_resources = {
            "influence": sender_res[0],
            "resources": sender_res[1],
            "information": sender_res[2],
            "force": sender_res[3]
        }

        for resource, amount in offer.items():
            if sender_resources.get(resource, 0) < amount:
                logger.error(
                    f"Sender {sender_id} lacks {resource}: needs {amount}, has {sender_resources.get(resource, 0)}")
                return 0

        # Check if receiver exists
        cursor.execute("SELECT player_id FROM players WHERE player_id = ?", (receiver_id,))
        if not cursor.fetchone():
            logger.error(f"Receiver {receiver_id} not found")
            return 0

        # Create the offer
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO trade_offers 
            (sender_id, receiver_id, status, created_at)
            VALUES (?, ?, 'pending', ?)
        """, (sender_id, receiver_id, now))

        offer_id = cursor.lastrowid

        # Add offered resources
        for resource, amount in offer.items():
            cursor.execute("""
                INSERT INTO trade_resources
                (offer_id, resource_type, amount, is_offer)
                VALUES (?, ?, ?, 1)
            """, (offer_id, resource, amount))

        # Add requested resources
        for resource, amount in request.items():
            cursor.execute("""
                INSERT INTO trade_resources
                (offer_id, resource_type, amount, is_offer) 
                VALUES (?, ?, ?, 0)
            """, (offer_id, resource, amount))

        # Deduct offered resources from sender
        for resource, amount in offer.items():
            cursor.execute(
                f"UPDATE resources SET {resource} = {resource} - ? WHERE player_id = ?",
                (amount, sender_id)
            )

        return offer_id

    except Exception as e:
        logger.error(f"Error creating trade offer: {e}")
        return 0


@db_transaction
def accept_trade_offer(conn, offer_id: int, receiver_id: int) -> bool:
    """
    Accept and execute a trade offer.

    Args:
        conn: Database connection
        offer_id: ID of the trade offer
        receiver_id: ID of player accepting the offer

    Returns:
        bool: True if trade completed successfully
    """
    try:
        cursor = conn.cursor()

        # Verify offer exists and is pending
        cursor.execute("""
            SELECT sender_id, status 
            FROM trade_offers 
            WHERE offer_id = ? AND receiver_id = ? AND status = 'pending'
        """, (offer_id, receiver_id))

        offer = cursor.fetchone()
        if not offer:
            logger.error(f"Trade offer {offer_id} not found, not pending, or not for receiver {receiver_id}")
            return False

        sender_id = offer[0]

        # Get trade details
        cursor.execute("""
            SELECT resource_type, amount, is_offer 
            FROM trade_resources 
            WHERE offer_id = ?
        """, (offer_id,))

        resources = cursor.fetchall()
        offered = {}
        requested = {}

        for resource_type, amount, is_offer in resources:
            if is_offer:
                offered[resource_type] = amount
            else:
                requested[resource_type] = amount

        # Verify receiver has sufficient resources for the requested items
        cursor.execute(
            """
            SELECT influence, resources, information, force
            FROM resources
            WHERE player_id = ?
            """,
            (receiver_id,)
        )

        receiver_res = cursor.fetchone()
        if not receiver_res:
            logger.error(f"Receiver {receiver_id} not found or has no resources")
            return False

        receiver_resources = {
            "influence": receiver_res[0],
            "resources": receiver_res[1],
            "information": receiver_res[2],
            "force": receiver_res[3]
        }

        for resource, amount in requested.items():
            if receiver_resources.get(resource, 0) < amount:
                logger.error(
                    f"Receiver {receiver_id} lacks {resource}: needs {amount}, has {receiver_resources.get(resource, 0)}")
                return False

        # Execute trade - transfer requested resources
        for resource, amount in requested.items():
            cursor.execute(
                f"UPDATE resources SET {resource} = {resource} - ? WHERE player_id = ?",
                (amount, receiver_id)
            )

            cursor.execute(
                f"UPDATE resources SET {resource} = {resource} + ? WHERE player_id = ?",
                (amount, sender_id)
            )

        # Transfer offered resources to receiver (already deducted from sender)
        for resource, amount in offered.items():
            cursor.execute(
                f"UPDATE resources SET {resource} = {resource} + ? WHERE player_id = ?",
                (amount, receiver_id)
            )

        # Update offer status
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            UPDATE trade_offers 
            SET status = 'completed', completed_at = ?
            WHERE offer_id = ?
        """, (now, offer_id))

        return True

    except Exception as e:
        logger.error(f"Error accepting trade offer: {e}")
        return False


@db_transaction
def cancel_trade_offer(conn, offer_id: int, sender_id: int) -> bool:
    """
    Cancel a trade offer and refund resources.

    Args:
        conn: Database connection
        offer_id: ID of the trade to cancel
        sender_id: ID of the player who created the offer

    Returns:
        bool: True if cancellation was successful
    """
    try:
        cursor = conn.cursor()

        # Verify offer exists, belongs to sender, and is still pending
        cursor.execute("""
            SELECT status 
            FROM trade_offers 
            WHERE offer_id = ? AND sender_id = ? AND status = 'pending'
        """, (offer_id, sender_id))

        if not cursor.fetchone():
            logger.error(f"Trade offer {offer_id} not found, not pending, or not from sender {sender_id}")
            return False

        # Get offered resources to refund
        cursor.execute("""
            SELECT resource_type, amount 
            FROM trade_resources 
            WHERE offer_id = ? AND is_offer = 1
        """, (offer_id,))

        resources = cursor.fetchall()

        # Refund resources to sender
        for resource_type, amount in resources:
            cursor.execute(
                f"UPDATE resources SET {resource_type} = {resource_type} + ? WHERE player_id = ?",
                (amount, sender_id)
            )

        # Update offer status
        now = datetime.datetime.now().isoformat()
        cursor.execute("""
            UPDATE trade_offers 
            SET status = 'cancelled', completed_at = ?
            WHERE offer_id = ?
        """, (now, offer_id))

        return True

    except Exception as e:
        logger.error(f"Error cancelling trade offer: {e}")
        return False


@db_transaction
def get_active_trades(conn) -> List[Dict[str, Any]]:
    """Get list of active trade offers."""
    try:
        cursor = conn.cursor()
        now = datetime.datetime.now().isoformat()

        cursor.execute("""
            SELECT to.offer_id, to.sender_id, to.receiver_id, to.status, to.created_at,
                   p1.character_name as sender_name,
                   p2.character_name as receiver_name
            FROM trade_offers to
            JOIN players p1 ON to.sender_id = p1.player_id
            LEFT JOIN players p2 ON to.receiver_id = p2.player_id
            WHERE to.status = 'pending'
            AND to.created_at > datetime('now', '-24 hours')
            ORDER BY to.created_at DESC
        """)

        offers = []
        for row in cursor.fetchall():
            offer_id, sender_id, receiver_id, status, created_at, sender_name, receiver_name = row

            # Get offered resources
            cursor.execute("""
                SELECT resource_type, amount
                FROM trade_resources
                WHERE offer_id = ? AND is_offer = 1
            """, (offer_id,))

            offer_resources = {r[0]: r[1] for r in cursor.fetchall()}

            # Get requested resources
            cursor.execute("""
                SELECT resource_type, amount
                FROM trade_resources
                WHERE offer_id = ? AND is_offer = 0
            """, (offer_id,))

            request_resources = {r[0]: r[1] for r in cursor.fetchall()}

            offers.append({
                'id': offer_id,
                'sender_id': sender_id,
                'sender_name': sender_name,
                'receiver_id': receiver_id,
                'receiver_name': receiver_name,
                'status': status,
                'created_at': created_at,
                'offer_resources': offer_resources,
                'request_resources': request_resources
            })

        return offers

    except Exception as e:
        logger.error(f"Error getting active trades: {e}")
        return []


@db_transaction
def get_trade_info(conn, trade_id: int) -> Optional[Dict[str, Any]]:
    """Get detailed information about a trade."""
    try:
        cursor = conn.cursor()

        # Get trade information
        cursor.execute("""
            SELECT to.sender_id, to.receiver_id, to.status, to.created_at,
                   p1.character_name as sender_name,
                   p2.character_name as receiver_name
            FROM trade_offers to
            JOIN players p1 ON to.sender_id = p1.player_id
            LEFT JOIN players p2 ON to.receiver_id = p2.player_id
            WHERE to.offer_id = ?
        """, (trade_id,))

        row = cursor.fetchone()
        if not row:
            return None

        sender_id, receiver_id, status, created_at, sender_name, receiver_name = row

        # Get resources
        cursor.execute("""
            SELECT resource_type, amount, is_offer
            FROM trade_resources
            WHERE offer_id = ?
        """, (trade_id,))

        resources = cursor.fetchall()
        offer_resources = {r[0]: r[1] for r in resources if r[2]}
        request_resources = {r[0]: r[1] for r in resources if not r[2]}

        return {
            'id': trade_id,
            'sender_id': sender_id,
            'sender_name': sender_name,
            'receiver_id': receiver_id,
            'receiver_name': receiver_name,
            'status': status,
            'created_at': created_at,
            'offer_resources': offer_resources,
            'request_resources': request_resources
        }

    except Exception as e:
        logger.error(f"Error getting trade info: {e}")
        return None


def format_trade_info(trade_id: int, lang: str = "en") -> str:
    """Format trade information for display."""
    with db_connection_pool.get_connection() as conn:
        trade = get_trade_info(conn, trade_id)
        if not trade:
            return get_text("trade_not_found", lang)

        # Format resources
        offer_list = [f"{amount} {resource}" for resource, amount in trade['offer_resources'].items()]
        request_list = [f"{amount} {resource}" for resource, amount in trade['request_resources'].items()]

        created_time = datetime.datetime.fromisoformat(trade['created_at'])
        formatted_time = created_time.strftime("%Y-%m-%d %H:%M")

        lines = [
            f"*{get_text('trade_offer', lang)}*",
            f"{get_text('sender', lang)}: {trade['sender_name']}",
            f"{get_text('receiver', lang)}: {trade['receiver_name'] or get_text('not_specified', lang)}",
            "",
            f"{get_text('offering', lang)}: {', '.join(offer_list) or get_text('nothing', lang)}",
            f"{get_text('requesting', lang)}: {', '.join(request_list) or get_text('nothing', lang)}",
            "",
            f"{get_text('status', lang)}: {get_text(trade['status'], lang)}",
            f"{get_text('created', lang)}: {formatted_time}"
        ]

        return "\n".join(lines)


def get_active_trade_list(lang: str = "en") -> str:
    """Get formatted list of active trades."""
    with db_connection_pool.get_connection() as conn:
        trades = get_active_trades(conn)

        if not trades:
            return get_text("no_active_trades", lang)

        trade_list = [get_text("active_trades_header", lang)]
        for trade in trades:
            # Format resources
            offer_list = [f"{amount} {get_text(resource, lang)}" for resource, amount in
                          trade['offer_resources'].items()]
            request_list = [f"{amount} {get_text(resource, lang)}" for resource, amount in
                            trade['request_resources'].items()]

            # Format creation time
            created_time = datetime.datetime.fromisoformat(trade['created_at'])
            formatted_time = created_time.strftime("%Y-%m-%d %H:%M")

            trade_list.append(
                f"*{get_text('trade_id', lang)}: {trade['id']}*\n"
                f"{get_text('sender', lang)}: {trade['sender_name']}\n"
                f"{get_text('offering', lang)}: {', '.join(offer_list)}\n"
                f"{get_text('requesting', lang)}: {', '.join(request_list)}\n"
                f"{get_text('created', lang)}: {formatted_time}\n"
            )

        return "\n".join(trade_list).strip()