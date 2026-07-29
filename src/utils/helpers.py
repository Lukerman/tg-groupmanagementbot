def get_user_mention(user):
    """Get user mention string"""
    if user.username:
        return f"@{user.username}"
    return user.first_name

def format_welcome_message(template: str, user, chat_title: str) -> str:
    """Format welcome message with variables"""
    mention = get_user_mention(user)
    return template.format(
        mention=mention,
        title=chat_title,
        name=user.first_name
    )

def format_goodbye_message(template: str, user) -> str:
    """Format goodbye message with variables"""
    mention = get_user_mention(user)
    return template.format(
        mention=mention,
        name=user.first_name
    )

def is_admin(user_id: int, admin_list: list) -> bool:
    """Check if user is admin"""
    return any(admin.user.id == user_id for admin in admin_list)

def parse_time(time_str: str) -> int:
    """Parse time string like '1h', '30m', '7d' to seconds"""
    if not time_str:
        return 0
    
    multipliers = {'s': 1, 'm': 60, 'h': 3600, 'd': 86400}
    
    try:
        unit = time_str[-1].lower()
        value = int(time_str[:-1])
        
        if unit in multipliers:
            return value * multipliers[unit]
        return value  # Assume seconds if no unit
    except (ValueError, IndexError):
        return 0
