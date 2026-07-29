from sqlalchemy import create_engine, Column, Integer, String, Boolean, BigInteger, Text
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from src.configs.settings import DATABASE_URL

Base = declarative_base()
engine = create_engine(DATABASE_URL.replace("sqlite:///", "sqlite:///bot_database.db"))
SessionLocal = sessionmaker(bind=engine)

class GroupSettings(Base):
    __tablename__ = "group_settings"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, unique=True, nullable=False)
    protection_enabled = Column(Boolean, default=True)
    anti_spam = Column(Boolean, default=True)
    delete_links = Column(Boolean, default=False)
    delete_forwards = Column(Boolean, default=False)
    captcha_enabled = Column(Boolean, default=False)
    welcome_enabled = Column(Boolean, default=True)
    goodbye_enabled = Column(Boolean, default=False)
    welcome_message = Column(Text, default="Welcome {mention} to {title}! 🎉")
    goodbye_message = Column(Text, default="{mention} has left the group.")
    warn_limit = Column(Integer, default=3)
    theme = Column(String, default="default")

class UserWarnings(Base):
    __tablename__ = "user_warnings"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    warnings = Column(Integer, default=0)
    reason = Column(Text, nullable=True)

class Filter(Base):
    __tablename__ = "filters"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    keyword = Column(String, nullable=False)
    response = Column(Text, nullable=False)

class Note(Base):
    __tablename__ = "notes"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    name = Column(String, nullable=False)
    content = Column(Text, nullable=False)

class CaptchaChallenge(Base):
    __tablename__ = "captcha_challenges"
    
    id = Column(Integer, primary_key=True)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    answer = Column(Integer, nullable=False)
    message_id = Column(BigInteger, nullable=False)

Base.metadata.create_all(engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def get_session():
    return SessionLocal()
