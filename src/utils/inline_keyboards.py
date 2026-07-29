"""Advanced Inline Keyboards with Theme Support"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from typing import Optional

class ThemeManager:
    """Manage color themes for inline buttons using emojis"""
    
    THEMES = {
        "default": {"primary": "🔵", "success": "✅", "warning": "⚠️", "danger": "❌", "info": "ℹ️"},
        "ocean": {"primary": "🌊", "success": "🐬", "warning": "🌪️", "danger": "🦈", "info": "🐟"},
        "forest": {"primary": "🌲", "success": "🍀", "warning": "🍂", "danger": "🔥", "info": "🦉"},
        "sunset": {"primary": "🌅", "success": "🌺", "warning": "🧡", "danger": "🌋", "info": "🦋"},
        "cyber": {"primary": "💜", "success": "💚", "warning": "💛", "danger": "❤️", "info": "💙"},
        "galaxy": {"primary": "⭐", "success": "🪐", "warning": "☄️", "danger": "🌑", "info": "🌙"},
        "fire": {"primary": "🔥", "success": "✨", "warning": "💥", "danger": "☠️", "info": "🎆"},
        "ice": {"primary": "❄️", "success": "💎", "warning": "🌨️", "danger": "🧊", "info": "🌊"},
    }
    
    @classmethod
    def get_theme(cls, theme_name: str) -> dict:
        return cls.THEMES.get(theme_name, cls.THEMES["default"])
    
    @classmethod
    def get_all_themes(cls) -> list:
        return list(cls.THEMES.keys())


class InlineBuilder:
    """Build advanced inline keyboards with themes"""
    
    def __init__(self, theme: str = "default"):
        self.theme = ThemeManager.get_theme(theme)
        self.keyboard = []
    
    def set_theme(self, theme: str):
        self.theme = ThemeManager.get_theme(theme)
        return self
    
    def row(self, *buttons: InlineKeyboardButton) -> 'InlineBuilder':
        self.keyboard.append(list(buttons))
        return self
    
    def btn(self, text: str, callback_data: str, emoji_type: str = "primary") -> InlineKeyboardButton:
        emoji = self.theme.get(emoji_type, self.theme["primary"])
        return InlineKeyboardButton(f"{emoji} {text}", callback_data=callback_data)
    
    def btn_url(self, text: str, url: str, emoji_type: str = "primary") -> InlineKeyboardButton:
        emoji = self.theme.get(emoji_type, self.theme["primary"])
        return InlineKeyboardButton(f"{emoji} {text}", url=url)
    
    def btn_switch(self, text: str, switch_inline_query: str, emoji_type: str = "primary") -> InlineKeyboardButton:
        emoji = self.theme.get(emoji_type, self.theme["primary"])
        return InlineKeyboardButton(f"{emoji} {text}", switch_inline_query=switch_inline_query)
    
    def build(self) -> InlineKeyboardMarkup:
        return InlineKeyboardMarkup(self.keyboard)
    
    def clear(self) -> 'InlineBuilder':
        self.keyboard = []
        return self


# Pre-built Keyboard Templates

def get_main_menu_keyboard(theme: str = "default") -> InlineKeyboardMarkup:
    """Main menu for group settings"""
    builder = InlineBuilder(theme)
    return (builder
        .row(builder.btn("🛡️ Protection", "settings_protection"),
             builder.btn("👋 Welcome", "settings_welcome"))
        .row(builder.btn("⚠️ Filters", "settings_filters"),
             builder.btn("📝 Notes", "settings_notes"))
        .row(builder.btn("🎨 Theme Colors", "settings_theme"),
             builder.btn("🔧 Permissions", "settings_permissions"))
        .row(builder.btn("📊 Statistics", "settings_stats"),
             builder.btn("❓ Help", "settings_help"))
        .build())


def get_protection_settings_keyboard(theme: str = "default") -> InlineKeyboardMarkup:
    """Protection settings panel"""
    builder = InlineBuilder(theme)
    return (builder
        .row(builder.btn("🔗 Delete Links", "protect_links_toggle"),
             builder.btn("📤 Delete Forwarded", "protect_forward_toggle"))
        .row(builder.btn("🤖 Anti-Bot", "protect_bot_toggle"),
             builder.btn("📢 Channel Posts", "protect_channel_toggle"))
        .row(builder.btn("🧩 CAPTCHA", "protect_captcha_toggle"),
             builder.btn("🚫 Anti-Spam", "protect_spam_toggle"))
        .row(builder.btn("🔙 Back", "settings_back_main"))
        .build())


def get_welcome_settings_keyboard(theme: str = "default") -> InlineKeyboardMarkup:
    """Welcome message settings"""
    builder = InlineBuilder(theme)
    return (builder
        .row(builder.btn("✅ Enable Welcome", "welcome_enable"),
             builder.btn("❌ Disable Welcome", "welcome_disable"))
        .row(builder.btn("✏️ Set Message", "welcome_set_msg"),
             builder.btn("👁️ Preview", "welcome_preview"))
        .row(builder.btn("🚪 Goodbye Messages", "goodbye_settings"))
        .row(builder.btn("🔙 Back", "settings_back_main"))
        .build())


def get_theme_selection_keyboard(current_theme: str = "default") -> InlineKeyboardMarkup:
    """Theme/color selection keyboard"""
    builder = InlineBuilder("default")
    themes = ThemeManager.get_all_themes()
    
    buttons = []
    for theme in themes:
        emoji = "✅" if theme == current_theme else "⚪"
        buttons.append(InlineKeyboardButton(f"{emoji} {theme.capitalize()}", f"theme_set_{theme}"))
        if len(buttons) % 2 == 0:
            builder.row(*buttons)
            buttons = []
    
    if buttons:
        builder.row(*buttons)
    
    builder.row(builder.btn("🔙 Back", "settings_back_main", "info"))
    return builder.build()


def get_moderation_actions_keyboard(user_id: int, theme: str = "default") -> InlineKeyboardMarkup:
    """Moderation actions for a specific user"""
    builder = InlineBuilder(theme)
    return (builder
        .row(builder.btn("⚠️ Warn", f"mod_warn_{user_id}"),
             builder.btn("🔇 Mute", f"mod_mute_{user_id}"))
        .row(builder.btn("🚫 Ban", f"mod_ban_{user_id}"),
             builder.btn("🔨 Kick", f"mod_kick_{user_id}"))
        .row(builder.btn("📋 Get Info", f"mod_info_{user_id}"),
             builder.btn("🗑️ Delete Msgs", f"mod_purge_{user_id}"))
        .row(builder.btn("❌ Close", "mod_close"))
        .build())


def get_captcha_keyboard(answer: str, theme: str = "default") -> InlineKeyboardMarkup:
    """CAPTCHA verification keyboard"""
    builder = InlineBuilder(theme)
    # Generate some wrong answers + correct one
    import random
    options = [answer]
    while len(options) < 4:
        wrong = str(random.randint(1, 20))
        if wrong not in options:
            options.append(wrong)
    random.shuffle(options)
    
    buttons = [builder.btn(opt, f"captcha_{opt}", "success" if opt == answer else "danger") for opt in options]
    return builder.row(*buttons).build()


def get_filters_list_keyboard(filters: list, theme: str = "default") -> InlineKeyboardMarkup:
    """List of filters with delete options"""
    builder = InlineBuilder(theme)
    
    for f in filters[:10]:  # Show max 10
        builder.row(
            InlineKeyboardButton(f"📄 {f.trigger}", callback_data=f"filter_view_{f.id}"),
            InlineKeyboardButton("🗑️", callback_data=f"filter_delete_{f.id}")
        )
    
    builder.row(builder.btn("➕ Add Filter", "filter_add"),
                builder.btn("🔙 Back", "settings_back_main"))
    return builder.build()


def get_notes_list_keyboard(notes: list, theme: str = "default") -> InlineKeyboardMarkup:
    """List of notes with delete options"""
    builder = InlineBuilder(theme)
    
    for note in notes[:10]:
        builder.row(
            InlineKeyboardButton(f"📝 {note.name}", callback_data=f"note_view_{note.id}"),
            InlineKeyboardButton("🗑️", callback_data=f"note_delete_{note.id}")
        )
    
    builder.row(builder.btn("➕ Add Note", "note_add"),
                builder.btn("🔙 Back", "settings_back_main"))
    return builder.build()


def get_permissions_keyboard(settings, theme: str = "default") -> InlineKeyboardMarkup:
    """Chat permissions settings"""
    builder = InlineBuilder(theme)
    
    perms = [
        ("messages", settings.can_send_messages, "💬"),
        ("media", settings.can_send_media, "🖼️"),
        ("polls", settings.can_send_polls, "📊"),
        ("other", settings.can_send_other, "📎"),
        ("previews", settings.can_add_web_previews, "🌐"),
        ("info", settings.can_change_info, "ℹ️"),
        ("invite", settings.can_invite_users, "👥"),
        ("pin", settings.can_pin_messages, "📌"),
    ]
    
    for perm_name, enabled, icon in perms:
        status = "ON" if enabled else "OFF"
        emoji_type = "success" if enabled else "danger"
        builder.row(
            InlineKeyboardButton(f"{icon} {perm_name.capitalize()}: {status}", 
                               callback_data=f"perm_toggle_{perm_name}")
        )
    
    builder.row(builder.btn("🔙 Back", "settings_back_main"))
    return builder.build()


def get_warnings_keyboard(user_id: int, warning_count: int, max_warnings: int, theme: str = "default") -> InlineKeyboardMarkup:
    """Warning management keyboard"""
    builder = InlineBuilder(theme)
    
    builder.row(InlineKeyboardButton(
        f"⚠️ Warnings: {warning_count}/{max_warnings}", 
        callback_data="warnings_count"
    ))
    
    builder.row(
        builder.btn("➕ Add Warning", f"warn_add_{user_id}"),
        builder.btn("➖ Remove Warning", f"warn_remove_{user_id}")
    )
    builder.row(
        builder.btn("🗑️ Clear All", f"warn_clear_{user_id}"),
        builder.btn("📋 List Warnings", f"warn_list_{user_id}")
    )
    builder.row(builder.btn("❌ Close", "mod_close"))
    
    return builder.build()
