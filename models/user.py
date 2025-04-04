"""
User model definition.

Defines the User entity with fields for name and email,
extending the base CRUD-enabled ORM model.
"""
from sqlalchemy import Column, String
from models.base import BaseModel


class User(BaseModel):
    """
    ORM model representing a user.

    Attributes:
        id (int): Primary key inherited from BaseModel.
        created_at (datetime): Creation timestamp inherited from BaseModel.
        updated_at (datetime): Last update timestamp inherited from BaseModel.
        name (str): User's name. Cannot be null.
        email (str): User's email address. Must be unique and indexed.
    """

    # Explicitly set the table name to "users" instead of using the default lowercase class name.
    __tablename__ = "users"

    name = Column(String, nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
