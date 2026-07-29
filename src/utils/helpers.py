"""Utility Helper Functions"""
import re
import random
import string
from datetime import datetime, timedelta
from typing import Optional, Tuple
from telegram import User, Chat


def extract_time(time_str: str) -> Optional[datetime]:
    """Extract time from strings like '1m', '2h', '3d', '1w'"""
    if not time_str:
        return None
    
    match = re.match(r'^(\d+)([smhdw])$', time_str.lower())
    if not match:
        return None
    
    value, unit = match.groups()
    value = int(value)
    
    now = datetime.utcnow()
    if unit == 's':
        return now + timedelta(seconds=value)
    elif unit == 'm':
        return now + timedelta(minutes=value)
    elif unit == 'h':
        return now + timedelta(hours=value)
    elif unit == 'd':
        return now + timedelta(days=value)
    elif unit == 'w':
        return now + timedelta(weeks=value)
    
    return None


def format_time(dt: datetime) -> str:
    """Format datetime to human readable string"""
    now = datetime.utcnow()
    diff = dt - now
    
    if diff.total_seconds() < 0:
        return "expired"
    
    seconds = int(diff.total_seconds())
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        return f"{seconds // 60} minutes"
    elif seconds < 86400:
        return f"{seconds // 3600} hours"
    else:
        return f"{seconds // 86400} days"


def generate_captcha() -> Tuple[str, str]:
    """Generate a simple math CAPTCHA"""
    num1 = random.randint(1, 10)
    num2 = random.randint(1, 10)
    question = f"{num1} + {num2} = ?"
    answer = str(num1 + num2)
    return question, answer


def generate_random_string(length: int = 8) -> str:
    """Generate random alphanumeric string"""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def mention_html(user: User) -> str:
    """Create HTML mention for user"""
    if user.username:
        return f'<a href="tg://user?id={user.id}">{user.first_name}</a>'
    return f'<a href="tg://user?id={user.id}">{user.first_name or "User"}</a>'


def truncate_text(text: str, max_length: int = 100) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length - 3] + "..."


def is_link(text: str) -> bool:
    """Check if text contains URL/link"""
    url_pattern = r'https?://[^\s]+'
    return bool(re.search(url_pattern, text))


def is_forwarded_message(message) -> bool:
    """Check if message is forwarded"""
    return message.forward_from is not None or message.forward_from_chat is not None


def count_mentions(message) -> int:
    """Count mentions in message"""
    return len(message.entities) if message.entities else 0


def count_hashtags(text: str) -> int:
    """Count hashtags in text"""
    return len(re.findall(r'#\w+', text))


def parse_filter_command(text: str) -> Tuple[str, str]:
    """Parse filter command: /filter trigger | response"""
    if '|' not in text:
        return "", ""
    
    parts = text.split('|', 1)
    trigger = parts[0].strip()
    response = parts[1].strip() if len(parts) > 1 else ""
    
    return trigger, response


def parse_note_command(text: str) -> Tuple[str, str]:
    """Parse note command: /addnote name | content"""
    if '|' not in text:
        return "", ""
    
    parts = text.split('|', 1)
    name = parts[0].strip()
    content = parts[1].strip() if len(parts) > 1 else ""
    
    return name, content


def get_chat_type_emoji(chat_type: str) -> str:
    """Get emoji for chat type"""
    emojis = {
        "private": "👤",
        "group": "👥",
        "supergroup": "🏢",
        "channel": "📢",
    }
    return emojis.get(chat_type, "❓")


def format_number(num: int) -> str:
    """Format large numbers with K, M suffixes"""
    if num >= 1000000:
        return f"{num / 1000000:.1f}M"
    elif num >= 1000:
        return f"{num / 1000:.1f}K"
    return str(num)


async def check_user_admin(chat_id: int, user_id: int, context) -> bool:
    """Check if user is admin in chat"""
    try:
        chat_member = await context.bot.get_chat_member(chat_id, user_id)
        return chat_member.status in ['creator', 'administrator']
    except Exception:
        return False


async def check_bot_admin(chat_id: int, context) -> bool:
    """Check if bot is admin in chat"""
    try:
        bot_member = await context.bot.get_chat_member(chat_id, context.bot.id)
        return bot_member.status in ['creator', 'administrator']
    except Exception:
        return False
