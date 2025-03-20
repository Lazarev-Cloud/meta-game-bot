import sqlite3
from typing import Dict, List, Optional, Any, Tuple
from db.game_queries import (
    get_active_trades,
    get_trade_info,
    create_trade_offer,
    accept_trade,
    cancel_trade
)
from languages import get_text
from db.queries import db_connection_pool, db_transaction
import logging
import datetime
import json
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

@db_transaction
def create_trade_offer(sender_id: int, receiver_id: int, offer: Dict[str, int], request: Dict[str, int]) -> int:
    """
    Create a new trade offer.
    
    Args:
        sender_id: ID of player making the offer
        receiver_id: ID of player receiving the offer  
        offer: Dict of resources being offered {resource_type: amount}
        request: Dict of resources being requested {resource_type: amount}
        
    Returns:
        offer_id of created offer, or 0 if failed
    """
    try:
        # Validate offer and request
        if not validate_resource_offer(offer) or not validate_resource_offer(request):
            logger.error("Invalid resource offer or request")
            return 0
            
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verify sender has sufficient resources
            sender_resources = get_player_resources(sender_id)
            for resource, amount in offer.items():
                if sender_resources.get(resource, 0) < amount:
                    logger.error(f"Sender {sender_id} lacks {resource}: needs {amount}, has {sender_resources.get(resource, 0)}")
                    return 0
                    
            # Create the offer
            cursor.execute("""
                INSERT INTO trade_offers 
                (sender_id, receiver_id, status, created_at)
                VALUES (?, ?, 'pending', datetime('now'))
            """, (sender_id, receiver_id))
                
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
                    
            return offer_id
            
    except Exception as e:
        logger.error(f"Error creating trade offer: {e}")
        return 0

@db_transaction
def accept_trade_offer(offer_id: int, receiver_id: int) -> bool:
    """
    Accept and execute a trade offer.
    
    Args:
        offer_id: ID of the trade offer
        receiver_id: ID of player accepting the offer
        
    Returns:
        bool: True if trade completed successfully
    """
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Verify offer exists and is pending
            cursor.execute("""
                SELECT sender_id, status 
                FROM trade_offers 
                WHERE offer_id = ? AND receiver_id = ? AND status = 'pending'
            """, (offer_id, receiver_id))
            
            offer = cursor.fetchone()
            if not offer:
                return False
                
            sender_id = offer[0]
            
            # Get trade details
            cursor.execute("""
                SELECT resource_type, amount, is_offer 
                FROM trade_resources 
                WHERE offer_id = ?
            """, (offer_id,))
            
            resources = cursor.fetchall()
            offered = {r[0]: r[1] for r in resources if r[2]}
            requested = {r[0]: r[1] for r in resources if not r[2]}
            
            # Verify both players have sufficient resources
            sender_resources = get_player_resources(sender_id)
            receiver_resources = get_player_resources(receiver_id)
            
            for resource, amount in offered.items():
                if sender_resources.get(resource, 0) < amount:
                    return False
                    
            for resource, amount in requested.items():
                if receiver_resources.get(resource, 0) < amount:
                    return False
            
            # Execute trade
            # Transfer offered resources
            for resource, amount in offered.items():
                update_player_resources(sender_id, resource, -amount)
                update_player_resources(receiver_id, resource, amount)
                    
            # Transfer requested resources
            for resource, amount in requested.items():
                update_player_resources(receiver_id, resource, -amount)
                update_player_resources(sender_id, resource, amount)
                
            # Update offer status
            cursor.execute("""
                UPDATE trade_offers 
                SET status = 'completed', completed_at = datetime('now')
                WHERE offer_id = ?
            """, (offer_id,))
                
            # Add trade notification
            cursor.execute("""
                INSERT INTO notifications 
                (player_id, title, content, created_at)
                VALUES 
                (?, ?, ?, datetime('now')),
                (?, ?, ?, datetime('now'))
            """, (
                sender_id, 
                get_text("trade_completed_title", "ru"),
                get_text("trade_completed_sender", "ru", receiver_id=receiver_id),
                receiver_id,
                get_text("trade_completed_title", "ru"),
                get_text("trade_completed_receiver", "ru", sender_id=sender_id)
            ))
            
            return True
            
    except Exception as e:
        logger.error(f"Error accepting trade offer: {e}")
        return False

def validate_resource_offer(offer: Dict[str, int]) -> bool:
    """Validate resource offer dictionary."""
    valid_resources = {"influence", "resources", "information", "force"}
    
    try:
        # Check resource types
        for resource_type, amount in offer.items():
            if resource_type not in valid_resources:
                logger.error(f"Invalid resource type in offer: {resource_type}")
                return False
            
            # Check amount is positive
            if not isinstance(amount, int) or amount <= 0:
                logger.error(f"Invalid amount for {resource_type}: {amount}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Error validating resource offer: {e}")
        return False

def format_trade_info(trade_id: int, lang: str = "en") -> str:
    """Format trade information for display."""
    with db_connection_pool.get_connection() as conn:
        trade = get_trade_info(trade_id, conn)
        if not trade:
            return get_text("trade_not_found", lang)
        
        # Format expiration time
        expires_at = datetime.datetime.fromisoformat(trade['expires_at'])
        formatted_expires = expires_at.strftime("%Y-%m-%d %H:%M")
        
        # Format resources
        offer_list = [f"{amount} {resource}" for resource, amount in trade['offer_resources'].items()]
        request_list = [f"{amount} {resource}" for resource, amount in trade['request_resources'].items()]
        
        info = [
            f"*{get_text('trade_offer', lang)}*",
            f"{get_text('seller', lang)}: {trade['seller_name']}",
            f"{get_text('offering', lang)}: {', '.join(offer_list)}",
            f"{get_text('requesting', lang)}: {', '.join(request_list)}",
            f"{get_text('status', lang)}: {get_text(trade['status'], lang)}",
            f"{get_text('expires', lang)}: {formatted_expires}"
        ]
        return "\n".join(info)

def get_available_trades(player_id: int, lang: str = "en") -> str:
    """Get formatted list of available trades."""
    trades = get_active_trades(player_id)
    
    if not trades:
        return get_text("no_trades", lang)

    trade_list = [get_text("available_trades", lang)]
    for trade in trades:
        trade_list.append(format_trade_info(trade['id'], lang))
        trade_list.append("")

    return "\n".join(trade_list).strip()

def create_trade(
    offerer_id: int,
    offered_resources: Dict[str, int],
    requested_resources: Dict[str, int],
    expiry: str,
    lang: str = "en"
) -> str:
    """Create a new trade offer and return confirmation."""
    try:
        trade_id = create_trade_offer(
            offerer_id=offerer_id,
            offered_resources=offered_resources,
            requested_resources=requested_resources,
            expiry=expiry
        )
        return get_text("trade_created", lang, params={"trade_id": trade_id})
    except Exception as e:
        return get_text("trade_creation_failed", lang)

def accept_trade_offer(player_id: int, trade_id: int, lang: str = "en") -> str:
    """Accept a trade offer and return confirmation."""
    try:
        accept_trade(player_id, trade_id)
        return get_text("trade_accepted", lang)
    except Exception as e:
        return get_text("trade_acceptance_failed", lang)

def cancel_trade_offer(trade_id: int, lang: str = "en") -> str:
    """Cancel a trade offer and return confirmation."""
    try:
        cancel_trade(trade_id)
        return get_text("trade_cancelled", lang)
    except Exception as e:
        return get_text("trade_cancellation_failed", lang)

@db_transaction
def get_active_trades(conn: Any) -> List[Dict[str, Any]]:
    """Get list of active trades."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, p.username as seller_name
            FROM trades t
            JOIN players p ON t.seller_id = p.player_id
            WHERE t.status = 'active'
                AND t.expires_at > ?
            ORDER BY t.created_at DESC
        """, (datetime.datetime.now().isoformat(),))
        
        trades = []
        for row in cursor.fetchall():
            trades.append({
                'id': row[0],
                'seller_id': row[1],
                'seller_name': row[7],
                'offer_resources': json.loads(row[2]),
                'request_resources': json.loads(row[3]),
                'created_at': row[4],
                'expires_at': row[5],
                'status': row[6]
            })
        return trades
    except Exception as e:
        logger.error(f"Error getting active trades: {e}")
        return []

@db_transaction
def get_trade_info(trade_id: int, conn: Any) -> Optional[Dict[str, Any]]:
    """Get detailed information about a trade."""
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.*, p.username as seller_name
            FROM trades t
            JOIN players p ON t.seller_id = p.player_id
            WHERE t.trade_id = ?
        """, (trade_id,))
        
        row = cursor.fetchone()
        if not row:
            return None
            
        return {
            'id': row[0],
            'seller_id': row[1],
            'seller_name': row[7],
            'offer_resources': json.loads(row[2]),
            'request_resources': json.loads(row[3]),
            'created_at': row[4],
            'expires_at': row[5],
            'status': row[6]
        }
    except Exception as e:
        logger.error(f"Error getting trade info: {e}")
        return None

@db_transaction
def accept_trade(trade_id: int, buyer_id: int, conn: Any) -> bool:
    """Accept a trade offer."""
    try:
        cursor = conn.cursor()
        
        # Get trade info
        cursor.execute("""
            SELECT seller_id, offer_resources, request_resources, status, expires_at
            FROM trades
            WHERE trade_id = ?
        """, (trade_id,))
        
        row = cursor.fetchone()
        if not row:
            return False
            
        seller_id, offer_resources, request_resources, status, expires_at = row
        
        # Check if trade is still active
        if status != 'active':
            return False
            
        # Check if trade hasn't expired
        if datetime.datetime.fromisoformat(expires_at) <= datetime.datetime.now():
            return False
        
        # Update trade status
        cursor.execute("""
            UPDATE trades
            SET status = 'completed',
                buyer_id = ?,
                completed_at = ?
            WHERE trade_id = ?
        """, (buyer_id, datetime.datetime.now().isoformat(), trade_id))
        
        return True
    except Exception as e:
        logger.error(f"Error accepting trade: {e}")
        return False

@db_transaction
def cancel_trade(trade_id: int, seller_id: int, conn: Any) -> bool:
    """Cancel a trade offer."""
    try:
        cursor = conn.cursor()
        
        # Verify trade exists and belongs to seller
        cursor.execute("""
            SELECT status
            FROM trades
            WHERE trade_id = ? AND seller_id = ?
        """, (trade_id, seller_id))
        
        row = cursor.fetchone()
        if not row or row[0] != 'active':
            return False
        
        # Cancel the trade
        cursor.execute("""
            UPDATE trades
            SET status = 'cancelled'
            WHERE trade_id = ?
        """, (trade_id,))
        
        return True
    except Exception as e:
        logger.error(f"Error cancelling trade: {e}")
        return False

def get_active_trade_list(lang: str = "en") -> str:
    """Get formatted list of active trades."""
    with db_connection_pool.get_connection() as conn:
        trades = get_active_trades(conn)
        
        if not trades:
            return get_text("no_active_trades", lang)
        
        trade_list = [get_text("available_trades", lang)]
        for trade in trades:
            # Format resources
            offer_list = [f"{amount} {resource}" for resource, amount in trade['offer_resources'].items()]
            request_list = [f"{amount} {resource}" for resource, amount in trade['request_resources'].items()]
            
            # Format expiration time
            expires_at = datetime.datetime.fromisoformat(trade['expires_at'])
            formatted_expires = expires_at.strftime("%Y-%m-%d %H:%M")
            
            trade_list.append(
                f"*{get_text('trade_id', lang)}: {trade['id']}*\n"
                f"{get_text('seller', lang)}: {trade['seller_name']}\n"
                f"{get_text('offering', lang)}: {', '.join(offer_list)}\n"
                f"{get_text('requesting', lang)}: {', '.join(request_list)}\n"
                f"{get_text('expires', lang)}: {formatted_expires}\n"
            )
        
        return "\n".join(trade_list).strip()

@db_transaction
def create_trade(seller_id: int, offered_resources: Dict[str, int], requested_resources: Dict[str, int], expiration_hours: int = 24) -> Optional[int]:
    """Create a new trade offer."""
    try:
        expiration_time = (datetime.now() + timedelta(hours=expiration_hours)).isoformat()
        
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    seller_id, offered_resources, requested_resources,
                    expiration_time, status
                )
                VALUES (?, ?, ?, ?, 'active')
            """, (
                seller_id,
                json.dumps(offered_resources),
                json.dumps(requested_resources),
                expiration_time
            ))
            return cursor.lastrowid
    except Exception as e:
        logger.error(f"Error creating trade: {e}")
        return None

@db_transaction
def get_trade_info(trade_id: int) -> Optional[Dict[str, Any]]:
    """Get information about a specific trade."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.trade_id, t.seller_id, t.offered_resources,
                       t.requested_resources, t.expiration_time, t.status,
                       p.username as seller_name
                FROM trades t
                JOIN players p ON t.seller_id = p.player_id
                WHERE t.trade_id = ?
            """, (trade_id,))
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                'id': row[0],
                'seller_id': row[1],
                'offered_resources': json.loads(row[2]),
                'requested_resources': json.loads(row[3]),
                'expiration_time': row[4],
                'status': row[5],
                'seller_name': row[6]
            }
    except Exception as e:
        logger.error(f"Error getting trade info: {e}")
        return None

@db_transaction
def get_active_trades() -> List[Dict[str, Any]]:
    """Get a list of active trades."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.trade_id, t.seller_id, t.offered_resources,
                       t.requested_resources, t.expiration_time,
                       p.username as seller_name
                FROM trades t
                JOIN players p ON t.seller_id = p.player_id
                WHERE t.status = 'active'
                  AND t.expiration_time > ?
                ORDER BY t.expiration_time
            """, (datetime.now().isoformat(),))
            
            trades = []
            for row in cursor.fetchall():
                trades.append({
                    'id': row[0],
                    'seller_id': row[1],
                    'offered_resources': json.loads(row[2]),
                    'requested_resources': json.loads(row[3]),
                    'expiration_time': row[4],
                    'seller_name': row[5]
                })
            return trades
    except Exception as e:
        logger.error(f"Error getting active trades: {e}")
        return []

@db_transaction
def accept_trade(trade_id: int, buyer_id: int) -> bool:
    """Accept a trade offer."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            
            # Get trade info
            cursor.execute("""
                SELECT seller_id, offered_resources, requested_resources, status
                FROM trades
                WHERE trade_id = ?
            """, (trade_id,))
            
            trade = cursor.fetchone()
            if not trade or trade[3] != 'active':
                return False
                
            seller_id, offered_resources, requested_resources = trade[:3]
            offered = json.loads(offered_resources)
            requested = json.loads(requested_resources)
            
            # Update trade status
            cursor.execute("""
                UPDATE trades
                SET status = 'completed', buyer_id = ?, completed_time = ?
                WHERE trade_id = ?
            """, (buyer_id, datetime.now().isoformat(), trade_id))
            
            # Transfer resources
            for resource, amount in offered.items():
                cursor.execute("""
                    UPDATE player_resources
                    SET amount = amount - ?
                    WHERE player_id = ? AND resource_type = ?
                """, (amount, seller_id, resource))
                
                cursor.execute("""
                    UPDATE player_resources
                    SET amount = amount + ?
                    WHERE player_id = ? AND resource_type = ?
                """, (amount, buyer_id, resource))
                
            for resource, amount in requested.items():
                cursor.execute("""
                    UPDATE player_resources
                    SET amount = amount - ?
                    WHERE player_id = ? AND resource_type = ?
                """, (amount, buyer_id, resource))
                
                cursor.execute("""
                    UPDATE player_resources
                    SET amount = amount + ?
                    WHERE player_id = ? AND resource_type = ?
                """, (amount, seller_id, resource))
            
            return True
    except Exception as e:
        logger.error(f"Error accepting trade: {e}")
        return False

@db_transaction
def cancel_trade(trade_id: int, seller_id: int) -> bool:
    """Cancel a trade offer."""
    try:
        with db_connection_pool.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades
                SET status = 'cancelled'
                WHERE trade_id = ? AND seller_id = ? AND status = 'active'
            """, (trade_id, seller_id))
            return cursor.rowcount > 0
    except Exception as e:
        logger.error(f"Error cancelling trade: {e}")
        return False

def format_trade_info(trade_id: int, lang: str = 'en') -> str:
    """Format trade information for display."""
    trade = get_trade_info(trade_id)
    if not trade:
        return get_text("trade_not_found", lang)
    
    expiration = datetime.fromisoformat(trade['expiration_time'])
    formatted_date = expiration.strftime("%Y-%m-%d %H:%M")
    
    lines = [
        f"*{get_text('trade_offer', lang)}*",
        f"{get_text('seller', lang)}: {trade['seller_name']}",
        "",
        f"*{get_text('offered_resources', lang)}*"
    ]
    
    for resource, amount in trade['offered_resources'].items():
        lines.append(f"- {amount} {get_text(resource, lang)}")
    
    lines.extend([
        "",
        f"*{get_text('requested_resources', lang)}*"
    ])
    
    for resource, amount in trade['requested_resources'].items():
        lines.append(f"- {amount} {get_text(resource, lang)}")
    
    lines.extend([
        "",
        f"{get_text('expires', lang)}: {formatted_date}",
        f"{get_text('status', lang)}: {get_text(trade['status'], lang)}"
    ])
    
    return "\n".join(lines)

def get_active_trade_list(lang: str = 'en') -> str:
    """Get a formatted list of active trades."""
    trades = get_active_trades()
    if not trades:
        return get_text("no_active_trades", lang)
    
    lines = [get_text("active_trades_header", lang)]
    for trade in trades:
        expiration = datetime.fromisoformat(trade['expiration_time'])
        formatted_date = expiration.strftime("%Y-%m-%d %H:%M")
        
        offered = ", ".join(f"{amount} {get_text(resource, lang)}"
                          for resource, amount in trade['offered_resources'].items())
        requested = ", ".join(f"{amount} {get_text(resource, lang)}"
                            for resource, amount in trade['requested_resources'].items())
        
        lines.extend([
            f"*{get_text('trade', lang)} #{trade['id']}*",
            f"{get_text('seller', lang)}: {trade['seller_name']}",
            f"{get_text('offers', lang)}: {offered}",
            f"{get_text('requests', lang)}: {requested}",
            f"{get_text('expires', lang)}: {formatted_date}",
            ""
        ])
    
    return "\n".join(lines).strip()