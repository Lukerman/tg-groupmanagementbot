"""Admin Commands Handler"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from src.models.database import ChatSettings, AdminRole
from src.utils.helpers import check_user_admin


async def lock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Lock chat permissions"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=update.chat_id)
            session.add(settings)
        
        # Disable permissions
        settings.can_send_messages = False
        settings.can_send_media = False
        settings.can_send_other = False
        settings.can_add_web_previews = False
        
        await session.commit()
    
    # Apply to chat
    try:
        await context.bot.set_chat_permissions(
            chat_id=update.chat_id,
            can_send_messages=False,
            can_send_media_messages=False,
            can_send_polls=True,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
        )
        await update.message.reply_text("🔒 Chat has been locked! Only admins can send messages.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error locking chat. Make sure I'm admin!\nError: {e}")


async def unlock_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unlock chat permissions"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=update.chat_id)
            session.add(settings)
        
        # Enable default permissions
        settings.can_send_messages = True
        settings.can_send_media = True
        settings.can_send_other = True
        settings.can_add_web_previews = True
        
        await session.commit()
    
    # Apply to chat
    try:
        await context.bot.set_chat_permissions(
            chat_id=update.chat_id,
            can_send_messages=True,
            can_send_media_messages=True,
            can_send_polls=True,
            can_send_other_messages=True,
            can_add_web_page_previews=True,
            can_change_info=False,
            can_invite_users=True,
            can_pin_messages=False,
        )
        await update.message.reply_text("🔓 Chat has been unlocked! Members can send messages.")
    except Exception as e:
        await update.message.reply_text(f"❌ Error unlocking chat.\nError: {e}")


async def antispam_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle anti-spam"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=update.chat_id)
            session.add(settings)
        
        settings.anti_spam = not settings.anti_spam
        await session.commit()
        
        status = "✅ enabled" if settings.anti_spam else "❌ disabled"
        await update.message.reply_text(f"Anti-spam has been {status}!")


async def antilink_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle link deletion"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=update.chat_id)
            session.add(settings)
        
        settings.delete_links = not settings.delete_links
        await session.commit()
        
        status = "✅ enabled" if settings.delete_links else "❌ disabled"
        await update.message.reply_text(f"Link deletion has been {status}!")


async def theme_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Show theme selection"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    from src.utils.inline_keyboards import get_theme_selection_keyboard
    from src.models.database import ChatSettings
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.scalar_one_or_none()
        
        current_theme = settings.theme if settings else "default"
    
    await update.message.reply_text(
        f"🎨 <b>Current Theme:</b> {current_theme.capitalize()}\n\n"
        "Select a new theme:",
        parse_mode='HTML',
        reply_markup=get_theme_selection_keyboard(current_theme)
    )


def setup_admin_commands(application):
    """Setup admin command handlers"""
    application.add_handler(CommandHandler("lock", lock_command))
    application.add_handler(CommandHandler("unlock", unlock_command))
    application.add_handler(CommandHandler("antispam", antispam_command))
    application.add_handler(CommandHandler("antilink", antilink_command))
    application.add_handler(CommandHandler("theme", theme_command))
