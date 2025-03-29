from sqlalchemy import Column, Integer, DateTime, func
from sqlalchemy.orm import declared_attr
from app.db import Base, SessionLocal


class BaseModel(Base):
    __abstract__ = True

    id = Column(Integer, primary_key=True, index=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    # CREATE
    @classmethod
    def create(cls, **kwargs):
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
        db = SessionLocal()
        result = db.query(cls).filter(cls.id == id).first()
        db.close()
        return result

    @classmethod
    def get_by(cls, **filters):
        """
        Найти первую запись по произвольным полям.
        Пример: User.get_by(email="admin@example.com")
        """
        db = SessionLocal()
        result = db.query(cls).filter_by(**filters).first()
        db.close()
        return result

    @classmethod
    def all(cls):
        db = SessionLocal()
        result = db.query(cls).all()
        db.close()
        return result

    # UPDATE
    def update(self, **kwargs):
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
        db = SessionLocal()
        db.delete(self)
        db.commit()
        db.close()
