import os

# Bot Configuration
BOT_TOKEN = os.getenv("BOT_TOKEN", "8699561436:AAFzxCPxZiKnlu2mGVh2EFfujrcif5WfIWk")
ADMIN_ID = int(os.getenv("ADMIN_ID", "1778070005"))

# Database
DATABASE_URL = "sqlite:///bot_database.db"

# Color Themes with Emoji Palettes
COLOR_THEMES = {
    "default": {"name": "Default", "emojis": ["🔵", "⚪", "🔴", "🟢", "🟡"]},
    "ocean": {"name": "Ocean", "emojis": ["🌊", "💙", "🐬", "🐟", "⚓"]},
    "forest": {"name": "Forest", "emojis": ["🌲", "🍃", "🌿", "🍀", "🎋"]},
    "sunset": {"name": "Sunset", "emojis": ["🌅", "🧡", "🌞", "🍂", "🦊"]},
    "cyber": {"name": "Cyber", "emojis": ["💜", "🤖", "⚡", "👾", "💾"]},
    "galaxy": {"name": "Galaxy", "emojis": ["🌌", "⭐", "🌠", "🚀", "🪐"]},
    "fire": {"name": "Fire", "emojis": ["🔥", "❤️", "🌶️", "🍁", "🧨"]},
    "ice": {"name": "Ice", "emojis": ["❄️", "🤍", "🧊", "🌨️", "☃️"]}
}

# Default settings
DEFAULT_SETTINGS = {
    "protection_enabled": True,
    "anti_spam": True,
    "delete_links": False,
    "delete_forwards": False,
    "captcha_enabled": False,
    "welcome_enabled": True,
    "goodbye_enabled": False,
    "warn_limit": 3,
    "theme": "default"
}
