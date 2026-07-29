"""Main Bot Entry Point"""
import logging
from telegram import Update, BotCommandScopeAllGroupChats, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from src.configs.settings import Config
from src.models.database import init_db
from src.handlers.admin import setup_admin_commands
from src.handlers.protection import setup_protection_handlers
from src.handlers.welcome import setup_welcome_handlers
from src.handlers.filters import setup_filter_handlers
from src.handlers.notes import setup_note_handlers
from src.handlers.moderation import setup_moderation_handlers
from src.handlers.inline import setup_inline_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    
    if update.chat_type == "private":
        welcome_text = (
            f"👋 Hello {user.first_name}!\n\n"
            "I'm an advanced group management bot with powerful features:\n\n"
            "🛡️ <b>Protection:</b> Anti-spam, anti-link, CAPTCHA\n"
            "👋 <b>Welcome:</b> Custom welcome/goodbye messages\n"
            "⚠️ <b>Filters:</b> Auto-responses to keywords\n"
            "📝 <b>Notes:</b> Save and share information\n"
            "🎨 <b>Themes:</b> Beautiful color themes for buttons\n"
            "🔧 <b>Moderation:</b> Ban, mute, warn users\n\n"
            "Add me to your group and make me admin to get started!\n\n"
            "Use /help in a group to see all commands."
        )
        
        from src.utils.inline_keyboards import InlineBuilder
        builder = InlineBuilder(Config.THEMES.get("default", {}))
        keyboard = (builder
            .row(builder.btn_url("➕ Add to Group", 
                                f"https://t.me/{context.bot.username}?startgroup=new"),
                builder.btn_url("📖 Documentation", "https://github.com/Lukerman/tg-groupmanagementbot"))
            .row(builder.btn("🎨 Change Theme", "theme_show_all"))
            .build())
        
        await update.message.reply_html(welcome_text, reply_markup=keyboard)


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = (
        "📚 <b>Help - Available Commands</b>\n\n"
        "<b>🛡️ Protection:</b>\n"
        "/lock - Lock chat permissions\n"
        "/unlock - Unlock chat permissions\n"
        "/antispam - Toggle anti-spam\n"
        "/antilink - Toggle link deletion\n\n"
        "<b>👋 Welcome:</b>\n"
        "/welcome - View welcome settings\n"
        "/setwelcome - Set welcome message\n"
        "/goodbye - Toggle goodbye messages\n\n"
        "<b>⚠️ Moderation:</b>\n"
        "/ban - Ban a user\n"
        "/mute - Mute a user\n"
        "/warn - Warn a user\n"
        "/kick - Kick a user\n"
        "/purge - Delete messages\n\n"
        "<b>📝 Filters & Notes:</b>\n"
        "/filter - Add a filter\n"
        "/filters - List all filters\n"
        "/addnote - Add a note\n"
        "/notes - List all notes\n\n"
        "<b>🎨 Settings:</b>\n"
        "/settings - Open settings panel\n"
        "/theme - Change button theme\n\n"
        "💡 <i>Tip: Use inline buttons for easy configuration!</i>"
    )
    
    from src.utils.inline_keyboards import get_main_menu_keyboard
    await update.message.reply_html(help_text, reply_markup=get_main_menu_keyboard())


async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Open settings panel"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    # Check if user is admin
    user = update.effective_user
    chat_member = await context.bot.get_chat_member(update.chat_id, user.id)
    if chat_member.status not in ['creator', 'administrator']:
        await update.message.reply_text("❌ Only admins can access settings!")
        return
    
    from src.utils.inline_keyboards import get_main_menu_keyboard
    from src.models.database import ChatSettings
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            ChatSettings.__table__.select().where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.fetchone()
        
        theme = settings.theme if settings else "default"
    
    settings_text = (
        f"⚙️ <b>Group Settings</b>\n\n"
        f"📝 <b>Chat:</b> {update.effective_chat.title}\n"
        f"🆔 <b>ID:</b> <code>{update.chat_id}</code>\n\n"
        "Select an option below to configure:"
    )
    
    await update.message.reply_html(settings_text, reply_markup=get_main_menu_keyboard(theme))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log errors caused by updates"""
    logger.error("Exception while handling an update:", exc_info=context.error)
    
    # Notify admin if possible
    if context.bot_data.get('admin_id'):
        try:
            await context.bot.send_message(
                chat_id=context.bot_data['admin_id'],
                text=f"⚠️ Error occurred:\n<code>{context.error}</code>",
                parse_mode='HTML'
            )
        except Exception:
            pass


async def post_init(application: Application):
    """Initialize bot after startup"""
    # Set commands for group chats
    commands = [
        BotCommand("start", "Start the bot"),
        BotCommand("help", "Show help message"),
        BotCommand("settings", "Open group settings panel"),
        BotCommand("ban", "Ban a user"),
        BotCommand("mute", "Mute a user"),
        BotCommand("warn", "Warn a user"),
        BotCommand("kick", "Kick a user"),
        BotCommand("welcome", "Configure welcome messages"),
        BotCommand("filter", "Add a filter"),
        BotCommand("addnote", "Add a note"),
        BotCommand("lock", "Lock chat permissions"),
        BotCommand("unlock", "Unlock chat permissions"),
        BotCommand("theme", "Change button theme"),
    ]
    
    await application.bot.set_my_commands(commands, scope=BotCommandScopeAllGroupChats())
    logger.info("Bot commands set successfully!")


def main():
    """Main function to run the bot"""
    logger.info("Starting Advanced Group Management Bot...")
    
    # Create application
    application = (
        Application.builder()
        .token(Config.BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Initialize database
    import asyncio
    async def setup_db():
        application.bot_data['db_session'] = await init_db(Config.DATABASE_URL)
        logger.info("Database initialized!")
    
    asyncio.get_event_loop().run_until_complete(setup_db())
    
    # Add handlers
    setup_admin_commands(application)
    setup_protection_handlers(application)
    setup_welcome_handlers(application)
    setup_filter_handlers(application)
    setup_note_handlers(application)
    setup_moderation_handlers(application)
    setup_inline_handlers(application)
    
    # Basic commands
    application.add_handler(CommandHandler("start", start_command))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    
    # Error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
