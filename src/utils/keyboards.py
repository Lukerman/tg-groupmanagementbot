from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def get_start_keyboard(is_admin: bool = False) -> InlineKeyboardMarkup:
    """Get start command keyboard"""
    buttons = [
        [InlineKeyboardButton("➕ Add to Group", url="https://t.me/YourBotName?startgroup=true")],
        [InlineKeyboardButton("⚙️ Settings", callback_data="settings")],
        [InlineKeyboardButton("📖 Help", callback_data="help")]
    ]
    if is_admin:
        buttons.append([InlineKeyboardButton("👮 Admin Panel", callback_data="admin_panel")])
    return InlineKeyboardMarkup(buttons)

def get_group_settings_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Get group settings inline keyboard"""
    buttons = [
        [
            InlineKeyboardButton("👋 Welcome", callback_data=f"setting_welcome_{chat_id}"),
            InlineKeyboardButton("🤖 Captcha", callback_data=f"setting_captcha_{chat_id}")
        ],
        [
            InlineKeyboardButton("🛡️ Anti-Spam", callback_data=f"setting_antispam_{chat_id}"),
            InlineKeyboardButton("💬 Anti-Flood", callback_data=f"setting_flood_{chat_id}")
        ],
        [
            InlineKeyboardButton("🚫 Banned Words", callback_data=f"setting_banned_{chat_id}"),
            InlineKeyboardKeyboardButton("🔗 Link Protection", callback_data=f"setting_links_{chat_id}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_moderation_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    """Get moderation tools keyboard"""
    buttons = [
        [
            InlineKeyboardButton("⚠️ Warn", callback_data=f"mod_warn_{chat_id}"),
            InlineKeyboardButton("📋 Warnings", callback_data=f"mod_warnings_{chat_id}")
        ],
        [
            InlineKeyboardButton("🔇 Mute", callback_data=f"mod_mute_{chat_id}"),
            InlineKeyboardButton("🔊 Unmute", callback_data=f"mod_unmute_{chat_id}")
        ],
        [
            InlineKeyboardButton("🚫 Ban", callback_data=f"mod_ban_{chat_id}"),
            InlineKeyboardButton("✅ Unban", callback_data=f"mod_unban_{chat_id}")
        ],
        [InlineKeyboardButton("🔙 Back", callback_data="back_to_main")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_yes_no_keyboard(action: str, data: str) -> InlineKeyboardMarkup:
    """Get yes/no confirmation keyboard"""
    buttons = [
        [
            InlineKeyboardButton("✅ Yes", callback_data=f"confirm_{action}_{data}"),
            InlineKeyboardButton("❌ No", callback_data=f"cancel_{action}_{data}")
        ]
    ]
    return InlineKeyboardMarkup(buttons)

def get_help_keyboard() -> InlineKeyboardMarkup:
    """Get help command keyboard"""
    buttons = [
        [InlineKeyboardButton("📖 Full Documentation", url="https://t.me/YourBotName")],
        [InlineKeyboardButton("💬 Support Chat", url="https://t.me/YourSupportChat")],
        [InlineKeyboardButton("🔙 Back", callback_data="start")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_admin_keyboard() -> InlineKeyboardMarkup:
    """Get admin panel keyboard"""
    buttons = [
        [InlineKeyboardButton("📊 Statistics", callback_data="admin_stats")],
        [InlineKeyboardButton("👥 Groups", callback_data="admin_groups")],
        [InlineKeyboardButton("🚨 Logs", callback_data="admin_logs")],
        [InlineKeyboardButton("⚙️ Bot Settings", callback_data="admin_bot_settings")],
        [InlineKeyboardButton("🔙 Back", callback_data="start")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_captcha_keyboard(user_id: int, answer: str) -> InlineKeyboardMarkup:
    """Get captcha verification keyboard with multiple choice"""
    import random
    
    # Generate wrong answers
    correct = int(answer)
    wrong_answers = []
    while len(wrong_answers) < 3:
        wrong = correct + random.randint(-5, 5)
        if wrong != correct and wrong > 0 and wrong not in wrong_answers:
            wrong_answers.append(wrong)
    
    options = wrong_answers + [correct]
    random.shuffle(options)
    
    buttons = [[InlineKeyboardButton(str(opt), callback_data=f"captcha_{user_id}_{opt}")] for opt in options]
    return InlineKeyboardMarkup(buttons)

def get_warning_keyboard(target_user_id: int, chat_id: int) -> InlineKeyboardMarkup:
    """Get warning management keyboard"""
    buttons = [
        [InlineKeyboardButton("📋 View Warnings", callback_data=f"warn_view_{target_user_id}_{chat_id}")],
        [InlineKeyboardButton("🗑️ Clear Warnings", callback_data=f"warn_clear_{target_user_id}_{chat_id}")],
        [InlineKeyboardButton("🔙 Back", callback_data="moderation")]
    ]
    return InlineKeyboardMarkup(buttons)

def get_purge_keyboard() -> InlineKeyboardMarkup:
    """Get message purge keyboard"""
    buttons = [
        [
            InlineKeyboardButton("🗑️ Delete 10", callback_data="purge_10"),
            InlineKeyboardButton("🗑️ Delete 50", callback_data="purge_50")
        ],
        [
            InlineKeyboardButton("🗑️ Delete 100", callback_data="purge_100"),
            InlineKeyboardButton("🗑️ Delete All", callback_data="purge_all")
        ],
        [InlineKeyboardButton("❌ Cancel", callback_data="purge_cancel")]
    ]
    return InlineKeyboardMarkup(buttons)
