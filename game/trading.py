import sqlite3
from typing import Dict

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
            
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Verify sender has sufficient resources
        sender_resources = get_player_resources(sender_id)
        for resource, amount in offer.items():
            if sender_resources.get(resource, 0) < amount:
                logger.error(f"Sender {sender_id} lacks {resource}: needs {amount}, has {sender_resources.get(resource, 0)}")
                conn.close()
                return 0
                
        # Create the offer
        with conn:
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
                
        conn.close()
        return offer_id
        
    except Exception as e:
        logger.error(f"Error creating trade offer: {e}")
        return 0

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
        conn = sqlite3.connect('belgrade_game.db')
        cursor = conn.cursor()
        
        # Verify offer exists and is pending
        cursor.execute("""
            SELECT sender_id, status 
            FROM trade_offers 
            WHERE offer_id = ? AND receiver_id = ? AND status = 'pending'
        """, (offer_id, receiver_id))
        
        offer = cursor.fetchone()
        if not offer:
            conn.close()
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
                conn.close()
                return False
                
        for resource, amount in requested.items():
            if receiver_resources.get(resource, 0) < amount:
                conn.close()
                return False
        
        # Execute trade in a transaction
        with conn:
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
        
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"Error accepting trade offer: {e}")
        return False

def validate_resource_offer(offer: Dict[str, int]) -> bool:
    """Validate resource offer dictionary."""
    valid_resources = {"influence", "resources", "information", "force"}
    
    try:
        # Проверяем типы ресурсов
        for resource_type, amount in offer.items():
            if resource_type not in valid_resources:
                logger.error(f"Invalid resource type in offer: {resource_type}")
                return False
            
            # Проверяем что количество положительное
            if not isinstance(amount, int) or amount <= 0:
                logger.error(f"Invalid amount for {resource_type}: {amount}")
                return False
                
        return True
        
    except Exception as e:
        logger.error(f"Error validating resource offer: {e}")
        return False