from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from src.configs.settings import COLOR_THEMES

def get_theme_emojis(theme_name: str) -> list:
    """Get emoji palette for a theme"""
    theme = COLOR_THEMES.get(theme_name, COLOR_THEMES["default"])
    return theme["emojis"]

def build_settings_keyboard(chat_id: int, theme: str = "default") -> InlineKeyboardMarkup:
    """Build themed settings inline keyboard"""
    emojis = get_theme_emojis(theme)
    
    keyboard = [
        [
            InlineKeyboardButton(f"{emojis[0]} Protection", callback_data=f"settings_protection_{chat_id}"),
            InlineKeyboardButton(f"{emojis[1]} Anti-Spam", callback_data=f"settings_antispam_{chat_id}")
        ],
        [
            InlineKeyboardButton(f"{emojis[2]} Delete Links", callback_data=f"settings_links_{chat_id}"),
            InlineKeyboardButton(f"{emojis[3]} Delete Forwards", callback_data=f"settings_forwards_{chat_id}")
        ],
        [
            InlineKeyboardButton(f"{emojis[4]} CAPTCHA", callback_data=f"settings_captcha_{chat_id}"),
            InlineKeyboardButton("👋 Welcome", callback_data=f"settings_welcome_{chat_id}")
        ],
        [
            InlineKeyboardButton("⚙️ Permissions", callback_data=f"settings_permissions_{chat_id}"),
            InlineKeyboardButton("🎨 Change Theme", callback_data=f"settings_theme_{chat_id}")
        ],
        [
            InlineKeyboardButton("📝 Filters", callback_data=f"settings_filters_{chat_id}"),
            InlineKeyboardButton("📒 Notes", callback_data=f"settings_notes_{chat_id}")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_settings")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def build_theme_keyboard() -> InlineKeyboardMarkup:
    """Build theme selection keyboard"""
    keyboard = []
    row = []
    
    for theme_key, theme_data in COLOR_THEMES.items():
        emoji = theme_data["emojis"][0]
        row.append(InlineKeyboardButton(f"{emoji} {theme_data['name']}", callback_data=f"set_theme_{theme_key}"))
        
        if len(row) == 2:
            keyboard.append(row)
            row = []
    
    if row:
        keyboard.append(row)
    
    keyboard.append([InlineKeyboardButton("« Back", callback_data="back_to_settings")])
    
    return InlineKeyboardMarkup(keyboard)

def build_moderation_keyboard(user_id: int, theme: str = "default") -> InlineKeyboardMarkup:
    """Build themed moderation keyboard"""
    emojis = get_theme_emojis(theme)
    
    keyboard = [
        [
            InlineKeyboardButton(f"{emojis[2]} Ban", callback_data=f"mod_ban_{user_id}"),
            InlineKeyboardButton(f"{emojis[3]} Mute", callback_data=f"mod_mute_{user_id}"),
            InlineKeyboardButton(f"{emojis[4]} Warn", callback_data=f"mod_warn_{user_id}")
        ],
        [
            InlineKeyboardButton("👢 Kick", callback_data=f"mod_kick_{user_id}"),
            InlineKeyboardButton("✅ Unmute", callback_data=f"mod_unmute_{user_id}")
        ],
        [
            InlineKeyboardButton("❌ Close", callback_data="close_mod")
        ]
    ]
    
    return InlineKeyboardMarkup(keyboard)

def build_captcha_keyboard(answer: int) -> InlineKeyboardMarkup:
    """Build CAPTCHA verification keyboard"""
    import random
    
    # Generate 4 options with one correct answer
    options = [answer]
    while len(options) < 4:
        opt = random.randint(1, 20)
        if opt not in options:
            options.append(opt)
    
    random.shuffle(options)
    
    keyboard = [
        [InlineKeyboardButton(str(opt), callback_data=f"captcha_{opt}")]
        for opt in options
    ]
    
    return InlineKeyboardMarkup(keyboard)

def build_filters_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Build filters management keyboard"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Filter", callback_data=f"filter_add_{chat_id}")],
        [InlineKeyboardButton("📋 View Filters", callback_data=f"filter_list_{chat_id}")],
        [InlineKeyboardButton("« Back", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_notes_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Build notes management keyboard"""
    keyboard = [
        [InlineKeyboardButton("➕ Add Note", callback_data=f"note_add_{chat_id}")],
        [InlineKeyboardButton("📋 View Notes", callback_data=f"note_list_{chat_id}")],
        [InlineKeyboardButton("« Back", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(keyboard)
