"""Welcome Message Handlers"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from src.models.database import ChatSettings
from src.utils.helpers import check_user_admin


async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View welcome settings"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
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
            await session.commit()
    
    status_welcome = "✅ Enabled" if settings.welcome_enabled else "❌ Disabled"
    status_goodbye = "✅ Enabled" if settings.goodbye_enabled else "❌ Disabled"
    
    text = (
        f"👋 <b>Welcome Settings</b>\n\n"
        f"Welcome Messages: {status_welcome}\n"
        f"Goodbye Messages: {status_goodbye}\n\n"
        f"<b>Current Welcome:</b>\n<code>{settings.welcome_message}</code>\n\n"
        f"<b>Current Goodbye:</b>\n<code>{settings.goodbye_message}</code>"
    )
    
    from src.utils.inline_keyboards import get_welcome_settings_keyboard
    await update.message.reply_html(text, reply_markup=get_welcome_settings_keyboard(settings.theme))


async def setwelcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set custom welcome message"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    # Get message text after command
    args = context.args
    if not args:
        await update.message.reply_html(
            "✏️ <b>Set Welcome Message</b>\n\n"
            "Usage: <code>/setwelcome Your message here</code>\n\n"
            "Available format options:\n"
            "<code>{mention}</code> - User mention\n"
            "<code>{title}</code> - Group title\n"
            "<code>{username}</code> - User username\n"
            "<code>{first_name}</code> - User first name\n\n"
            "Example:\n"
            "<code>/setwelcome Welcome {mention} to {title}! 🎉</code>"
        )
        return
    
    new_message = ' '.join(args)
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=update.chat_id)
            session.add(settings)
        
        settings.welcome_message = new_message
        settings.welcome_enabled = True
        await session.commit()
    
    await update.message.reply_html(
        f"✅ Welcome message updated!\n\n<code>{new_message}</code>"
    )


async def goodbye_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle goodbye messages"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
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
        
        settings.goodbye_enabled = not settings.goodbye_enabled
        await session.commit()
        
        status = "✅ enabled" if settings.goodbye_enabled else "❌ disabled"
        await update.message.reply_text(f"Goodbye messages have been {status}!")


async def welcome_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle welcome settings inline buttons"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=chat_id)
            session.add(settings)
            await session.commit()
        
        if data == "welcome_enable":
            settings.welcome_enabled = True
            await session.commit()
            await query.edit_message_text("✅ Welcome messages enabled!")
        
        elif data == "welcome_disable":
            settings.welcome_enabled = False
            await session.commit()
            await query.edit_message_text("❌ Welcome messages disabled!")
        
        elif data == "goodbye_settings":
            settings.goodbye_enabled = not settings.goodbye_enabled
            await session.commit()
            status = "✅ enabled" if settings.goodbye_enabled else "❌ disabled"
            await query.edit_message_text(f"Goodbye messages {status}!")
        
        elif data == "welcome_preview":
            preview_text = settings.welcome_message.format(
                mention=query.from_user.mention_html(),
                title="Your Group",
                username=f"@{query.from_user.username}" if query.from_user.username else "N/A",
                first_name=query.from_user.first_name
            )
            await query.message.reply_html(f"👁️ <b>Preview:</b>\n\n{preview_text}")
        
        elif data == "settings_back_main":
            from src.utils.inline_keyboards import get_main_menu_keyboard
            await query.edit_message_text(
                "⚙️ Select an option:",
                reply_markup=get_main_menu_keyboard(settings.theme)
            )


def setup_welcome_handlers(application):
    """Setup welcome handlers"""
    application.add_handler(CommandHandler("welcome", welcome_command))
    application.add_handler(CommandHandler("setwelcome", setwelcome_command))
    application.add_handler(CommandHandler("goodbye", goodbye_command))
    application.add_handler(CallbackQueryHandler(welcome_callback, pattern="^welcome_|^goodbye_|^settings_back_main$"))
