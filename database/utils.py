from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
import logging
from datetime import datetime

from .schema import Base, User, Language
from config import DATABASE_URL

logger = logging.getLogger(__name__)

# Create database engine and session
engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)

def get_user(telegram_id):
    """Get user by telegram ID"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error getting user {telegram_id}: {str(e)}")
        return None
    finally:
        session.close()

def create_user(telegram_id, username=None, first_name=None, last_name=None, detected_language=None):
    """Create a new user"""
    session = Session()
    try:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language=Language.EN,  # Default to English
            detected_language=detected_language,
            created_at=datetime.now(),
            last_active=datetime.now()
        )
        session.add(user)
        session.commit()
        return user
    except SQLAlchemyError as e:
        logger.error(f"Error creating user {telegram_id}: {str(e)}")
        session.rollback()
        return None
    finally:
        session.close()

def update_user_language(telegram_id, language):
    """Update user's preferred language"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.language = Language(language)
            user.last_active = datetime.now()
            session.commit()
            return True
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error updating language for user {telegram_id}: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close()

def update_detected_language(telegram_id, detected_language):
    """Update user's detected language"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.detected_language = Language(detected_language)
            session.commit()
            return True
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error updating detected language for user {telegram_id}: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close()

def get_user_language(telegram_id):
    """Get user's preferred language"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            return user.language.value
        return Language.EN.value  # Default to English if user not found
    except SQLAlchemyError as e:
        logger.error(f"Error getting language for user {telegram_id}: {str(e)}")
        return Language.EN.value  # Default to English on error
    finally:
        session.close()

def update_user_activity(telegram_id):
    """Update user's last active timestamp"""
    session = Session()
    try:
        user = session.query(User).filter(User.telegram_id == telegram_id).first()
        if user:
            user.last_active = datetime.now()
            session.commit()
            return True
        return False
    except SQLAlchemyError as e:
        logger.error(f"Error updating activity for user {telegram_id}: {str(e)}")
        session.rollback()
        return False
    finally:
        session.close() 