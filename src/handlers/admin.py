from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from src.models.database import get_session, GroupSettings
from src.utils.helpers import is_admin
from src.utils.inline_keyboards import build_settings_keyboard, build_theme_keyboard

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open group settings panel with inline buttons"""
    if not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        await update.effective_message.reply_text("This command only works in groups!")
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if admin
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        await update.effective_message.reply_text("❌ Only admins can use this command.")
        return
    
    db = get_session()
    try:
        settings = db.query(GroupSettings).filter_by(chat_id=chat.id).first()
        
        if not settings:
            settings = GroupSettings(chat_id=chat.id)
            db.add(settings)
            db.commit()
        
        theme = settings.theme or "default"
        
        await update.effective_message.reply_text(
            f"⚙️ **Group Settings for {chat.title}**\n\n"
            f"🎨 Theme: {theme.capitalize()}\n"
            f"🛡️ Protection: {'✅' if settings.protection_enabled else '❌'}\n"
            f"🤖 Anti-Spam: {'✅' if settings.anti_spam else '❌'}\n"
            f"🔗 Delete Links: {'✅' if settings.delete_links else '❌'}\n"
            f"↪️ Delete Forwards: {'✅' if settings.delete_forwards else '❌'}\n"
            f"🧩 CAPTCHA: {'✅' if settings.captcha_enabled else '❌'}\n"
            f"👋 Welcome: {'✅' if settings.welcome_enabled else '❌'}\n",
            parse_mode="HTML",
            reply_markup=build_settings_keyboard(chat.id, theme)
        )
    finally:
        db.close()

async def theme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Change group theme"""
    if not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        return
    
    await update.effective_message.reply_text(
        "🎨 **Select a Theme:**\n\nEach theme changes the emoji style of inline buttons.",
        parse_mode="HTML",
        reply_markup=build_theme_keyboard()
    )

async def set_welcome(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set custom welcome message"""
    if not update.effective_chat:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        return
    
    if not context.args:
        await update.effective_message.reply_text(
            "📝 Usage: /setwelcome message\n\nAvailable variables: {mention}, {title}, {name}"
        )
        return
    
    message = " ".join(context.args)
    
    db = get_session()
    try:
        settings = db.query(GroupSettings).filter_by(chat_id=chat.id).first()
        
        if not settings:
            settings = GroupSettings(chat_id=chat.id)
            db.add(settings)
        
        settings.welcome_message = message
        settings.welcome_enabled = True
        db.commit()
        
        await update.effective_message.reply_text("✅ Welcome message updated!")
    finally:
        db.close()

async def set_goodbye(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set custom goodbye message"""
    if not update.effective_chat:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        return
    
    if not context.args:
        await update.effective_message.reply_text(
            "📝 Usage: /setgoodbye message\n\nAvailable variables: {mention}, {name}"
        )
        return
    
    message = " ".join(context.args)
    
    db = get_session()
    try:
        settings = db.query(GroupSettings).filter_by(chat_id=chat.id).first()
        
        if not settings:
            settings = GroupSettings(chat_id=chat.id)
            db.add(settings)
        
        settings.goodbye_message = message
        settings.goodbye_enabled = True
        db.commit()
        
        await update.effective_message.reply_text("✅ Goodbye message updated!")
    finally:
        db.close()

async def locks_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock/unlock chat permissions"""
    if not update.effective_chat:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        return
    
    if not context.args:
        await update.effective_message.reply_text(
            "📝 Usage: /lock [messages|media|links] or /unlock [messages|media|links]"
        )
        return
    
    action = context.args[0].lower()
    lock_type = context.args[1].lower() if len(context.args) > 1 else "messages"
    
    try:
        if action == "lock":
            if lock_type == "messages":
                perms = ChatPermissions(can_send_messages=False)
            elif lock_type == "media":
                perms = ChatPermissions(can_send_media_messages=False)
            elif lock_type == "links":
                perms = ChatPermissions(can_add_web_page_previews=False)
            else:
                await update.effective_message.reply_text("Invalid lock type!")
                return
            
            await chat.set_permissions(perms)
            await update.effective_message.reply_text(f"🔒 Locked {lock_type}")
            
        elif action == "unlock":
            perms = ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
            await chat.set_permissions(perms)
            await update.effective_message.reply_text("🔓 Unlocked all permissions")
        else:
            await update.effective_message.reply_text("Use /lock or /unlock")
            
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Error: {str(e)}")
