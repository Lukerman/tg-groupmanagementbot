from sqlalchemy import Column, Integer, String, Boolean, BigInteger, DateTime, Text, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship
from datetime import datetime
from .database import Base

class Group(Base):
    __tablename__ = "groups"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    title = Column(String(255))
    is_active = Column(Boolean, default=True)
    welcome_enabled = Column(Boolean, default=False)
    welcome_message = Column(Text, nullable=True)
    captcha_enabled = Column(Boolean, default=False)
    anti_spam_enabled = Column(Boolean, default=False)
    antiflood_limit = Column(Integer, default=5)
    antiflood_window = Column(Integer, default=10)  # seconds
    banned_words = Column(Text, nullable=True)  # JSON list
    allowed_domains = Column(Text, nullable=True)  # JSON list
    admin_only_mode = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    settings = relationship("GroupSetting", back_populates="group", cascade="all, delete-orphan")
    warnings = relationship("Warning", back_populates="group", cascade="all, delete-orphan")


class GroupSetting(Base):
    __tablename__ = "group_settings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    key = Column(String(100), nullable=False)
    value = Column(Text, nullable=True)
    
    group = relationship("Group", back_populates="settings")
    __table_args__ = (UniqueConstraint('group_id', 'key', name='unique_group_setting'),)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(255), nullable=True)
    first_name = Column(String(255), nullable=True)
    last_name = Column(String(255), nullable=True)
    is_banned = Column(Boolean, default=False)
    ban_reason = Column(String(500), nullable=True)
    is_premium = Column(Boolean, default=False)
    language_code = Column(String(10), default="en")
    created_at = Column(DateTime, default=datetime.utcnow)
    
    warnings = relationship("Warning", back_populates="user", cascade="all, delete-orphan")


class Warning(Base):
    __tablename__ = "warnings"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    group_id = Column(Integer, ForeignKey("groups.id"), nullable=False)
    reason = Column(String(500))
    warned_by = Column(BigInteger)  # Admin user ID
    warned_at = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    user = relationship("User", back_populates="warnings")
    group = relationship("Group", back_populates="warnings")


class Mute(Base):
    __tablename__ = "mutes"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    muted_by = Column(BigInteger)
    reason = Column(String(500), nullable=True)
    mute_until = Column(DateTime, nullable=True)  # None for permanent
    created_at = Column(DateTime, default=datetime.utcnow)


class Ban(Base):
    __tablename__ = "bans"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    banned_by = Column(BigInteger)
    reason = Column(String(500), nullable=True)
    is_global = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class CaptchaSession(Base):
    __tablename__ = "captcha_sessions"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(BigInteger, nullable=False, index=True)
    group_id = Column(BigInteger, nullable=False, index=True)
    message_id = Column(BigInteger, nullable=True)
    answer = Column(String(50), nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_verified = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class LogEntry(Base):
    __tablename__ = "logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    group_id = Column(BigInteger, nullable=True, index=True)
    user_id = Column(BigInteger, nullable=True)
    action = Column(String(50), nullable=False)
    details = Column(Text, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)
