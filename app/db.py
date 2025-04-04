"""
Database configuration and SQLAlchemy session setup.

This module initializes the SQLAlchemy engine, session maker, and declarative base
using the application's environment settings.
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base
from app.config import settings


def get_db_url():
    """
    Build the SQLAlchemy-compatible database URL based on current settings.

    Returns:
        str: Database connection string.
    """
    if settings.db_engine == "sqlite":
        return f"sqlite:///./{settings.db_name}.db"
    return (f"{settings.db_engine}://{settings.db_user}:{settings.db_pass}"
            f"@{settings.db_host}:{settings.db_port}/{settings.db_name}")


# SQLAlchemy engine instance configured using application settings.
engine = create_engine(get_db_url(), echo=(settings.log_level == "DEBUG"))

# Factory for database sessions with default configuration.
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Declarative base class for defining SQLAlchemy ORM models.
Base = declarative_base()
