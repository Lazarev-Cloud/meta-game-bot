from .joint_actions import process_expired_joint_actions, cleanup_old_joint_actions

def process_game_cycle():
    """Process a game cycle"""
    try:
        # Process expired joint actions first
        process_expired_joint_actions()
        
        # ... existing cycle processing code ...
        
        # Clean up old joint actions at the end
        cleanup_old_joint_actions()
        
    except Exception as e:
        logger.error(f"Error processing game cycle: {e}") 