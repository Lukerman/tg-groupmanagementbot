"""Database Models for Group Management Bot"""
from sqlalchemy import Column, Integer, String, Boolean, BigInteger, Text, DateTime, ForeignKey
from sqlalchemy.ext.asyncio import AsyncAttrs, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, relationship
from datetime import datetime

class Base(AsyncAttrs, DeclarativeBase):
    pass

class ChatSettings(Base):
    __tablename__ = "chat_settings"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False, index=True)
    chat_title = Column(String(255))
    chat_type = Column(String(50))  # group, supergroup, channel
    
    # Welcome Settings
    welcome_enabled = Column(Boolean, default=True)
    welcome_message = Column(Text, default="Welcome {mention} to {title}! 🎉")
    goodbye_enabled = Column(Boolean, default=False)
    goodbye_message = Column(Text, default="{mention} left the group 👋")
    
    # Protection Settings
    protect_channels = Column(Boolean, default=False)
    delete_links = Column(Boolean, default=False)
    delete_forwarded = Column(Boolean, default=False)
    anti_spam = Column(Boolean, default=True)
    captcha_enabled = Column(Boolean, default=False)
    
    # Permissions
    can_send_messages = Column(Boolean, default=True)
    can_send_media = Column(Boolean, default=True)
    can_send_polls = Column(Boolean, default=True)
    can_send_other = Column(Boolean, default=True)
    can_add_web_previews = Column(Boolean, default=True)
    can_change_info = Column(Boolean, default=False)
    can_invite_users = Column(Boolean, default=True)
    can_pin_messages = Column(Boolean, default=False)
    
    # Theme/Color
    theme = Column(String(50), default="default")
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class User(Base):
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True)
    user_id = Column(BigInteger, unique=True, nullable=False, index=True)
    username = Column(String(100))
    first_name = Column(String(100))
    last_name = Column(String(100))
    is_bot = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    # Warnings count
    warning_count = Column(Integer, default=0)
    max_warnings = Column(Integer, default=3)
    
    # Mute settings
    is_muted = Column(Boolean, default=False)
    mute_until = Column(DateTime, nullable=True)
    
    # Timestamps
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class AdminRole(Base):
    __tablename__ = "admin_roles"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    role = Column(String(50), default="moderator")  # owner, admin, moderator
    permissions = Column(Text)  # JSON string of permissions
    
    granted_by = Column(BigInteger)
    granted_at = Column(DateTime, default=datetime.utcnow)
    
    expires_at = Column(DateTime, nullable=True)


class Warning(Base):
    __tablename__ = "warnings"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    user_id = Column(BigInteger, nullable=False)
    reason = Column(Text)
    
    warned_by = Column(BigInteger)
    warned_at = Column(DateTime, default=datetime.utcnow)


class Filter(Base):
    __tablename__ = "filters"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    trigger = Column(String(255), nullable=False)
    response = Column(Text, nullable=False)
    filter_type = Column(String(50), default="text")  # text, regex, sticker
    case_sensitive = Column(Boolean, default=False)
    
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)


class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    content = Column(Text, nullable=False)
    note_type = Column(String(50), default="text")  # text, photo, video, document
    
    created_by = Column(BigInteger)
    created_at = Column(DateTime, default=datetime.utcnow)


class CaptchaSession(Base):
    __tablename__ = "captcha_sessions"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    message_id = Column(Integer)
    answer = Column(String(50))
    solved = Column(Boolean, default=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)


async def init_db(database_url: str):
    engine = create_async_engine(database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    async_session = async_sessionmaker(engine, expire_on_commit=False)
    return async_session
