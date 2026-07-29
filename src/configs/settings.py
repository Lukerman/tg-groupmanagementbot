"""
Advanced Telegram Group Management Bot Configuration
"""
import os

class Config:
    # Bot Token (Get from @BotFather)
    BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
    
    # Database
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot_database.db")
    
    # Admin User IDs (Comma separated in env var)
    ADMINS = list(map(int, os.getenv("ADMINS", "").split(","))) if os.getenv("ADMINS") else []
    
    # Support Chat/Group
    SUPPORT_CHAT = os.getenv("SUPPORT_CHAT", "@your_support_group")
    
    # Bot Username (will be fetched automatically if not set)
    BOT_USERNAME = os.getenv("BOT_USERNAME", "")
    
    # Features Toggle
    ENABLE_SPAM_FILTER = True
    ENABLE_LINK_FILTER = True
    ENABLE_WELCOME = True
    ENABLE_CAPTCHA = True
    
    # Anti-Spam Settings
    MAX_MESSAGES_PER_MINUTE = 10
    MAX_HASHTAGS_PER_MESSAGE = 5
    MAX_MENTIONS_PER_MESSAGE = 10
    
    # Colors for Inline Buttons (Emoji-based themes)
    THEMES = {
        "default": {"primary": "🔵", "success": "🟢", "warning": "🟡", "danger": "🔴"},
        "ocean": {"primary": "🌊", "success": "🐬", "warning": "⚠️", "danger": "🦈"},
        "forest": {"primary": "🌲", "success": "🍀", "warning": "🍂", "danger": "🔥"},
        "sunset": {"primary": "🌅", "success": "🌺", "warning": "🧡", "danger": "🌋"},
        "cyber": {"primary": "💜", "success": "💚", "warning": "💛", "danger": "❤️"},
        "galaxy": {"primary": "⭐", "success": "🪐", "warning": "☄️", "danger": "🌑"},
    }
