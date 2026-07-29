from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from .models import Base, Group, User, Warning, Mute, Ban, CaptchaSession, LogEntry, GroupSetting
from datetime import datetime, timedelta
import json

DATABASE_URL = "sqlite:///data/bot.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

def init_db():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Group operations
def get_group(db, chat_id: int):
    return db.query(Group).filter(Group.chat_id == chat_id).first()

def create_group(db, chat_id: int, title: str):
    group = Group(chat_id=chat_id, title=title)
    db.add(group)
    db.commit()
    db.refresh(group)
    return group

def update_group_settings(db, chat_id: int, **kwargs):
    group = get_group(db, chat_id)
    if not group:
        group = create_group(db, chat_id, "Unknown")
    for key, value in kwargs.items():
        if hasattr(group, key):
            setattr(group, key, value)
    db.commit()
    db.refresh(group)
    return group

def get_group_setting(db, chat_id: int, key: str):
    group = get_group(db, chat_id)
    if not group:
        return None
    setting = db.query(GroupSetting).filter(
        GroupSetting.group_id == group.id,
        GroupSetting.key == key
    ).first()
    return setting.value if setting else None

def set_group_setting(db, chat_id: int, key: str, value: str):
    group = get_group(db, chat_id)
    if not group:
        group = create_group(db, chat_id, "Unknown")
    
    setting = db.query(GroupSetting).filter(
        GroupSetting.group_id == group.id,
        GroupSetting.key == key
    ).first()
    
    if setting:
        setting.value = value
    else:
        setting = GroupSetting(group_id=group.id, key=key, value=value)
        db.add(setting)
    db.commit()
    return setting

# User operations
def get_user(db, user_id: int):
    return db.query(User).filter(User.user_id == user_id).first()

def create_or_update_user(db, user_id: int, username: str = None, first_name: str = None, 
                          last_name: str = None, is_premium: bool = False, language_code: str = "en"):
    user = get_user(db, user_id)
    if not user:
        user = User(
            user_id=user_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            is_premium=is_premium,
            language_code=language_code
        )
        db.add(user)
    else:
        user.username = username
        user.first_name = first_name
        user.last_name = last_name
        user.is_premium = is_premium
        user.language_code = language_code
    db.commit()
    db.refresh(user)
    return user

def ban_user_globally(db, user_id: int, reason: str = None):
    user = get_user(db, user_id)
    if user:
        user.is_banned = True
        user.ban_reason = reason
        db.commit()
    return user

def unban_user_globally(db, user_id: int):
    user = get_user(db, user_id)
    if user:
        user.is_banned = False
        user.ban_reason = None
        db.commit()
    return user

# Warning operations
def add_warning(db, user_id: int, group_id: int, reason: str, warned_by: int):
    # Get or create user
    user = get_user(db, user_id)
    if not user:
        user = create_or_update_user(db, user_id)
    
    # Get or create group
    group = get_group(db, group_id)
    if not group:
        group = create_group(db, group_id, "Unknown")
    
    warning = Warning(
        user_id=user.id,
        group_id=group.id,
        reason=reason,
        warned_by=warned_by
    )
    db.add(warning)
    db.commit()
    
    # Count active warnings
    warning_count = db.query(Warning).filter(
        Warning.user_id == user.id,
        Warning.group_id == group.id,
        Warning.is_active == True
    ).count()
    
    return warning_count

def get_warnings(db, user_id: int, group_id: int):
    user = get_user(db, user_id)
    group = get_group(db, group_id)
    if not user or not group:
        return []
    return db.query(Warning).filter(
        Warning.user_id == user.id,
        Warning.group_id == group.id,
        Warning.is_active == True
    ).all()

def clear_warnings(db, user_id: int, group_id: int):
    user = get_user(db, user_id)
    group = get_group(db, group_id)
    if not user or not group:
        return 0
    warnings = db.query(Warning).filter(
        Warning.user_id == user.id,
        Warning.group_id == group.id,
        Warning.is_active == True
    ).all()
    count = len(warnings)
    for w in warnings:
        w.is_active = False
    db.commit()
    return count

# Mute operations
def mute_user(db, user_id: int, group_id: int, muted_by: int, duration: int = None, reason: str = None):
    mute_until = None
    if duration:
        mute_until = datetime.utcnow() + timedelta(seconds=duration)
    
    mute = Mute(
        user_id=user_id,
        group_id=group_id,
        muted_by=muted_by,
        mute_until=mute_until,
        reason=reason
    )
    db.add(mute)
    db.commit()
    return mute

def is_muted(db, user_id: int, group_id: int):
    mute = db.query(Mute).filter(
        Mute.user_id == user_id,
        Mute.group_id == group_id
    ).order_by(Mute.created_at.desc()).first()
    
    if not mute:
        return False
    
    if mute.mute_until and mute.mute_until < datetime.utcnow():
        return False
    
    return True

def unmute_user(db, user_id: int, group_id: int):
    mutes = db.query(Mute).filter(
        Mute.user_id == user_id,
        Mute.group_id == group_id
    ).all()
    for mute in mutes:
        db.delete(mute)
    db.commit()

# Ban operations
def ban_user(db, user_id: int, group_id: int, banned_by: int, reason: str = None, is_global: bool = False):
    ban = Ban(
        user_id=user_id,
        group_id=group_id,
        banned_by=banned_by,
        reason=reason,
        is_global=is_global
    )
    db.add(ban)
    db.commit()
    return ban

def is_banned(db, user_id: int, group_id: int):
    # Check global ban
    global_ban = db.query(Ban).filter(
        Ban.user_id == user_id,
        Ban.is_global == True
    ).first()
    if global_ban:
        return True
    
    # Check group ban
    group_ban = db.query(Ban).filter(
        Ban.user_id == user_id,
        Ban.group_id == group_id
    ).first()
    return group_ban is not None

def unban_user(db, user_id: int, group_id: int):
    bans = db.query(Ban).filter(
        Ban.user_id == user_id,
        Ban.group_id == group_id
    ).all()
    for ban in bans:
        db.delete(ban)
    db.commit()

# Captcha operations
def create_captcha_session(db, user_id: int, group_id: int, answer: str, expires_in: int = 300):
    session = CaptchaSession(
        user_id=user_id,
        group_id=group_id,
        answer=answer,
        expires_at=datetime.utcnow() + timedelta(seconds=expires_in)
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    return session

def get_captcha_session(db, user_id: int, group_id: int):
    session = db.query(CaptchaSession).filter(
        CaptchaSession.user_id == user_id,
        CaptchaSession.group_id == group_id,
        CaptchaSession.is_verified == False
    ).order_by(CaptchaSession.created_at.desc()).first()
    return session

def verify_captcha(db, session_id: int):
    session = db.query(CaptchaSession).filter(CaptchaSession.id == session_id).first()
    if session:
        session.is_verified = True
        db.commit()
    return session

def cleanup_expired_captchas(db):
    sessions = db.query(CaptchaSession).filter(
        CaptchaSession.expires_at < datetime.utcnow(),
        CaptchaSession.is_verified == False
    ).all()
    for s in sessions:
        db.delete(s)
    db.commit()
    return len(sessions)

# Log operations
def log_action(db, group_id: int, user_id: int, action: str, details: str = None):
    entry = LogEntry(
        group_id=group_id,
        user_id=user_id,
        action=action,
        details=details
    )
    db.add(entry)
    db.commit()
    return entry

def get_logs(db, group_id: int = None, limit: int = 50):
    query = db.query(LogEntry)
    if group_id:
        query = query.filter(LogEntry.group_id == group_id)
    return query.order_by(LogEntry.timestamp.desc()).limit(limit).all()
