"""
Base ORM model providing common CRUD operations.

Defines an abstract SQLAlchemy model with standard fields and utility methods
for create, read, update, and delete (CRUD) operations.
"""
from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import declared_attr
from app.db import Base, SessionLocal


class BaseModel(Base):
    """
    Abstract base class for ORM models.

    Attributes:
        id (int): Primary key identifier.
        created_at (datetime): Timestamp of creation.
        updated_at (datetime): Timestamp of the last update.

    Methods:
        create(**kwargs): Create and persist a new instance.
        get(id): Retrieve a record by its primary key.
        get_by(**filters): Retrieve the first record matching the given filters.
        all(): Retrieve all records.
        update(**kwargs): Update fields of the current instance and persist changes.
        delete(): Delete the current instance from the database.
    """

    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @classmethod
    @declared_attr
    def __tablename__(cls):
        """
        Automatically generate table name based on the class name in lowercase.

        Returns:
            str: The table name.
        """
        return cls.__name__.lower()

    # CREATE
    @classmethod
    def create(cls, **kwargs):
        """
        Create and persist a new instance in the database.

        Args:
            **kwargs: Fields and values to initialize the instance.

        Returns:
            BaseModel: The created and persisted instance.
        """
        db = SessionLocal()
        obj = cls(**kwargs)
        db.add(obj)
        db.commit()
        db.refresh(obj)
        db.close()
        return obj

    # READ
    @classmethod
    def get(cls, id: int):
        """
        Retrieve a record by its primary key.

        Args:
            id (int): The primary key identifier.

        Returns:
            BaseModel | None: The retrieved instance or None if not found.
        """
        db = SessionLocal()
        result = db.query(cls).filter(cls.id == id).first()
        db.close()
        return result

    @classmethod
    def get_by(cls, **filters):
        """
        Retrieve the first record matching the given filter criteria.

        Args:
            **filters: Field-value pairs to filter by.

        Example:
            User.get_by(email="admin@example.com")

        Returns:
            BaseModel | None: The retrieved instance or None if not found.
        """
        db = SessionLocal()
        result = db.query(cls).filter_by(**filters).first()
        db.close()
        return result

    @classmethod
    def all(cls):
        """
        Retrieve all records of this model from the database.

        Returns:
            list[BaseModel]: List of all instances.
        """
        db = SessionLocal()
        result = db.query(cls).all()
        db.close()
        return result

    # UPDATE
    def update(self, **kwargs):
        """
        Update fields of the current instance and persist changes.

        Args:
            **kwargs: Fields and new values to update.

        Returns:
            BaseModel: The updated instance.
        """
        db = SessionLocal()
        for key, value in kwargs.items():
            setattr(self, key, value)
        db.add(self)
        db.commit()
        db.refresh(self)
        db.close()
        return self

    # DELETE
    def delete(self):
        """
        Delete the current instance from the database.

        Returns:
            None
        """
        db = SessionLocal()
        db.delete(self)
        db.commit()
        db.close()
