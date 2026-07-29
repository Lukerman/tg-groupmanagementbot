import random
import string
from datetime import datetime, timedelta

def generate_captcha_answer(length: int = 6) -> str:
    """Generate a random captcha answer"""
    chars = string.ascii_uppercase + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def generate_math_captcha() -> tuple:
    """Generate a simple math captcha"""
    a = random.randint(1, 20)
    b = random.randint(1, 20)
    question = f"{a} + {b} = ?"
    answer = str(a + b)
    return question, answer

def format_time(seconds: int) -> str:
    """Format seconds into human readable time"""
    if seconds < 60:
        return f"{seconds} seconds"
    elif seconds < 3600:
        minutes = seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''}"
    elif seconds < 86400:
        hours = seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''}"
    else:
        days = seconds // 86400
        return f"{days} day{'s' if days > 1 else ''}"

def parse_time(time_str: str) -> int:
    """Parse time string like '5m', '1h', '2d' into seconds"""
    time_str = time_str.lower().strip()
    
    multipliers = {
        's': 1,
        'm': 60,
        'h': 3600,
        'd': 86400,
        'w': 604800
    }
    
    try:
        if time_str[-1] in multipliers:
            value = int(time_str[:-1])
            return value * multipliers[time_str[-1]]
        else:
            return int(time_str)
    except (ValueError, IndexError):
        return 0

def escape_markdown(text: str) -> str:
    """Escape special markdown characters"""
    special_chars = ['_', '*', '[', ']', '(', ')', '~', '`', '>', '#', '+', '-', '=', '|', '{', '}', '.', '!']
    for char in special_chars:
        text = text.replace(char, '\\' + char)
    return text

def mention_user(user_id: int, name: str) -> str:
    """Create a markdown mention"""
    return f"[{name}](tg://user?id={user_id})"

def truncate_text(text: str, max_length: int = 50) -> str:
    """Truncate text with ellipsis"""
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def is_valid_url(url: str) -> bool:
    """Basic URL validation"""
    return url.startswith(('http://', 'https://', 't.me/', 'telegram.me/'))

def extract_urls(text: str) -> list:
    """Extract URLs from text"""
    import re
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+|t\.me/[^\s<>"]+'
    return re.findall(url_pattern, text)

def contains_banned_word(text: str, banned_words: list) -> tuple:
    """Check if text contains any banned words"""
    text_lower = text.lower()
    for word in banned_words:
        if word.lower() in text_lower:
            return True, word
    return False, None

def get_user_status(is_muted: bool, is_banned: bool) -> str:
    """Get user status string"""
    if is_banned:
        return "🚫 Banned"
    elif is_muted:
        return "🔇 Muted"
    else:
        return "✅ Active"

def format_datetime(dt: datetime) -> str:
    """Format datetime to readable string"""
    return dt.strftime("%Y-%m-%d %H:%M:%S")

def get_relative_time(dt: datetime) -> str:
    """Get relative time description"""
    now = datetime.utcnow()
    diff = dt - now
    
    if diff.total_seconds() < 0:
        return "Expired"
    
    seconds = int(diff.total_seconds())
    return format_time(seconds) + " remaining"
