import datetime
from sqlalchemy import Column, Integer, String, Float, Text, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import relationship
from .database import Base

class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(64), primary_key=True, index=True)
    title = Column(String(255), default="Weather Query")
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc), onupdate=lambda: datetime.datetime.now(datetime.timezone.utc))

    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan")

class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    session_id = Column(String(64), ForeignKey("chat_sessions.id"), index=True)
    role = Column(String(20))  # 'user' or 'assistant'
    content = Column(Text, nullable=False)
    weather_snapshot = Column(Text, nullable=True)  # JSON serialized weather data
    alert_snapshot = Column(Text, nullable=True)    # JSON serialized alert data
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

    session = relationship("ChatSession", back_populates="messages")

class SavedLocation(Base):
    __tablename__ = "saved_locations"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    name = Column(String(100), nullable=False)
    state = Column(String(100), nullable=True)
    country = Column(String(100), default="India")
    lat = Column(Float, nullable=False)
    lon = Column(Float, nullable=False)
    is_default = Column(Boolean, default=False)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))

class AlertRecord(Base):
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    alert_id = Column(String(64), unique=True, index=True)
    region = Column(String(100), index=True)
    state = Column(String(100), nullable=True)
    hazard_type = Column(String(50))  # Cyclone, Heavy Rainfall, Heatwave, etc.
    severity = Column(String(20))     # GREEN, YELLOW, ORANGE, RED
    headline = Column(String(255))
    description = Column(Text)
    advisory = Column(Text)
    valid_from = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
    valid_until = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.datetime.now(datetime.timezone.utc))
