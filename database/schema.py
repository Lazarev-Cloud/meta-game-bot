from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, ForeignKey, DateTime, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
import enum

Base = declarative_base()

class Language(enum.Enum):
    EN = "en"
    RU = "ru"

class User(Base):
    __tablename__ = 'users'
    
    id = Column(Integer, primary_key=True)
    telegram_id = Column(Integer, unique=True, nullable=False)
    username = Column(String)
    first_name = Column(String)
    last_name = Column(String)
    language = Column(Enum(Language), default=Language.EN)
    detected_language = Column(Enum(Language))
    created_at = Column(DateTime)
    last_active = Column(DateTime)
    
    # Relationships
    resources = relationship("UserResource", back_populates="user")
    actions = relationship("UserAction", back_populates="user")
    districts = relationship("UserDistrict", back_populates="user")
    trades = relationship("Trade", back_populates="user")
    politicians = relationship("Politician", back_populates="user")

class UserResource(Base):
    __tablename__ = 'user_resources'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    resource_type = Column(String)
    amount = Column(Float)
    
    user = relationship("User", back_populates="resources")

class UserAction(Base):
    __tablename__ = 'user_actions'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    action_type = Column(String)
    status = Column(String)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    user = relationship("User", back_populates="actions")

class UserDistrict(Base):
    __tablename__ = 'user_districts'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    district_name = Column(String)
    influence = Column(Float)
    
    user = relationship("User", back_populates="districts")

class Trade(Base):
    __tablename__ = 'trades'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    offer_resource = Column(String)
    offer_amount = Column(Float)
    request_resource = Column(String)
    request_amount = Column(Float)
    status = Column(String)
    created_at = Column(DateTime)
    
    user = relationship("User", back_populates="trades")

class Politician(Base):
    __tablename__ = 'politicians'
    
    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey('users.id'))
    name = Column(String)
    party = Column(String)
    influence = Column(Float)
    status = Column(String)
    
    user = relationship("User", back_populates="politicians")

class GameCycle(Base):
    __tablename__ = 'game_cycles'
    
    id = Column(Integer, primary_key=True)
    cycle_number = Column(Integer)
    started_at = Column(DateTime)
    ended_at = Column(DateTime)
    events = Column(JSON)

def init_db(engine_url):
    """Initialize the database with the schema"""
    engine = create_engine(engine_url)
    Base.metadata.create_all(engine) 