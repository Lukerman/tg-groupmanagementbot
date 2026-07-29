from telegram import Update
from telegram.ext import ContextTypes
from src.models.database import get_session, GroupSettings
from src.utils.helpers import is_admin
from src.utils.inline_keyboards import build_settings_keyboard, build_theme_keyboard

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries from inline keyboards"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    # Close buttons
    if data == "close_settings" or data == "close_mod":
        await query.edit_message_text("Closed.")
        return
    
    if data == "back_to_settings":
        chat_id = query.message.chat.id
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            theme = settings.theme if settings else "default"
            
            await query.edit_message_text(
                f"⚙️ **Group Settings**\n\n🎨 Theme: {theme.capitalize()}",
                parse_mode="HTML",
                reply_markup=build_settings_keyboard(chat_id, theme)
            )
        finally:
            db.close()
        return
    
    # Theme selection
    if data.startswith("set_theme_"):
        theme_name = data.replace("set_theme_", "")
        chat_id = query.message.chat.id
        
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            if not settings:
                settings = GroupSettings(chat_id=chat_id)
                db.add(settings)
            
            settings.theme = theme_name
            db.commit()
            
            await query.edit_message_text(
                f"✅ Theme changed to **{theme_name.capitalize()}**!",
                parse_mode="HTML",
                reply_markup=build_theme_keyboard()
            )
        finally:
            db.close()
        return
    
    # Theme menu
    if data.startswith("settings_theme_"):
        await query.edit_message_text(
            "🎨 **Select a Theme:**",
            parse_mode="HTML",
            reply_markup=build_theme_keyboard()
        )
        return
    
    # Toggle protection
    if data.startswith("settings_protection_"):
        chat_id = int(data.split("_")[-1])
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            if settings:
                settings.protection_enabled = not settings.protection_enabled
                db.commit()
                
                await query.edit_message_text(
                    f"⚙️ **Group Settings**\n\n🛡️ Protection: {'✅ ON' if settings.protection_enabled else '❌ OFF'}",
                    parse_mode="HTML",
                    reply_markup=build_settings_keyboard(chat_id, settings.theme)
                )
        finally:
            db.close()
        return
    
    # Toggle anti-spam
    if data.startswith("settings_antispam_"):
        chat_id = int(data.split("_")[-1])
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            if settings:
                settings.anti_spam = not settings.anti_spam
                db.commit()
                
                await query.edit_message_text(
                    f"⚙️ **Group Settings**\n\n🤖 Anti-Spam: {'✅ ON' if settings.anti_spam else '❌ OFF'}",
                    parse_mode="HTML",
                    reply_markup=build_settings_keyboard(chat_id, settings.theme)
                )
        finally:
            db.close()
        return
    
    # Toggle delete links
    if data.startswith("settings_links_"):
        chat_id = int(data.split("_")[-1])
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            if settings:
                settings.delete_links = not settings.delete_links
                db.commit()
                
                await query.edit_message_text(
                    f"⚙️ **Group Settings**\n\n🔗 Delete Links: {'✅ ON' if settings.delete_links else '❌ OFF'}",
                    parse_mode="HTML",
                    reply_markup=build_settings_keyboard(chat_id, settings.theme)
                )
        finally:
            db.close()
        return
    
    # Toggle delete forwards
    if data.startswith("settings_forwards_"):
        chat_id = int(data.split("_")[-1])
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            if settings:
                settings.delete_forwards = not settings.delete_forwards
                db.commit()
                
                await query.edit_message_text(
                    f"⚙️ **Group Settings**\n\n↪️ Delete Forwards: {'✅ ON' if settings.delete_forwards else '❌ OFF'}",
                    parse_mode="HTML",
                    reply_markup=build_settings_keyboard(chat_id, settings.theme)
                )
        finally:
            db.close()
        return
    
    # Toggle CAPTCHA
    if data.startswith("settings_captcha_"):
        chat_id = int(data.split("_")[-1])
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            if settings:
                settings.captcha_enabled = not settings.captcha_enabled
                db.commit()
                
                await query.edit_message_text(
                    f"⚙️ **Group Settings**\n\n🧩 CAPTCHA: {'✅ ON' if settings.captcha_enabled else '❌ OFF'}",
                    parse_mode="HTML",
                    reply_markup=build_settings_keyboard(chat_id, settings.theme)
                )
        finally:
            db.close()
        return
    
    # Welcome settings info
    if data.startswith("settings_welcome_"):
        chat_id = int(data.split("_")[-1])
        db = get_session()
        try:
            settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
            
            await query.answer(
                f"Welcome: {'✅' if settings.welcome_enabled else '❌'}\n"
                f"Message: {settings.welcome_message}"[:200],
                show_alert=True
            )
        finally:
            db.close()
        return
    
    # Filters menu
    if data.startswith("settings_filters_"):
        chat_id = int(data.split("_")[-1])
        await query.edit_message_text(
            "📝 **Filters Management**\n\nUse /filter and /removefilter commands.",
            parse_mode="HTML",
            reply_markup=build_settings_keyboard(chat_id, "default")
        )
        return
    
    # Notes menu
    if data.startswith("settings_notes_"):
        chat_id = int(data.split("_")[-1])
        await query.edit_message_text(
            "📒 **Notes Management**\n\nUse /note and /removenote commands.",
            parse_mode="HTML",
            reply_markup=build_settings_keyboard(chat_id, "default")
        )
        return
    
    # Permissions info
    if data.startswith("settings_permissions_"):
        chat_id = int(data.split("_")[-1])
        await query.answer(
            "Use /lock and /unlock commands to manage permissions.\n"
            "Examples:\n/lock messages\n/unlock",
            show_alert=True
        )
        return
