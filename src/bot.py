import os
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
from sqlalchemy.orm import Session

# Import database and handlers
from src.database import init_db, engine, Base
from src.db_operations import get_db, create_or_update_user, get_group, update_group_settings
from src.handlers.moderation import get_moderation_handlers
from src.handlers.protection import get_protection_handlers

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('logs/bot.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Get bot token from environment
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
ADMIN_IDS = [int(x) for x in os.getenv('ADMIN_IDS', '').split(',') if x]

async def post_init(application: Application):
    """Initialize database after bot starts"""
    logger.info("Initializing database...")
    init_db()
    logger.info("Database initialized!")

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == 'start':
        await query.edit_message_text("👋 Welcome back! Use /start to begin.")
    elif data == 'help':
        await query.edit_message_text(
            "📖 **Help**\n\n"
            "I can help you manage your group with:\n"
            "• Welcome messages\n"
            "• CAPTCHA verification\n"
            "• Anti-spam & Anti-flood\n"
            "• Warnings, Mutes & Bans\n"
            "• Link protection\n\n"
            "Use /help for full command list.",
            parse_mode='Markdown'
        )
    elif data == 'settings':
        chat = update.effective_chat
        if not chat or chat.type == 'private':
            await query.edit_message_text("This only works in groups!")
            return
        await query.edit_message_text(f"⚙️ Group Settings for {chat.title}\n\nUse /settings for details.")
    elif data.startswith('setting_'):
        await query.edit_message_text("Settings configuration coming soon!")
    elif data.startswith('mod_'):
        await query.edit_message_text("Moderation tools coming soon!")
    elif data.startswith('warn_'):
        await query.edit_message_text("Warning management coming soon!")
    elif data == 'admin_panel':
        await query.edit_message_text("👮 Admin Panel\n\nBot statistics and controls coming soon!")
    else:
        await query.edit_message_text("Unknown action!")

async def error_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Log errors"""
    logger.error(f"Update {update} caused error: {context.error}")

def add_db_session(func):
    """Decorator to add database session to context"""
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        db = next(get_db())
        try:
            context.db_session = db
            return await func(update, context, *args, **kwargs)
        finally:
            db.close()
    return wrapper

def main():
    """Main function to run the bot"""
    if not BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN environment variable not set!")
        print("Error: Please set TELEGRAM_BOT_TOKEN environment variable")
        print("Example: export TELEGRAM_BOT_TOKEN='your_bot_token_here'")
        return
    
    logger.info("Starting bot...")
    
    # Create application
    application = (
        Application.builder()
        .token(BOT_TOKEN)
        .post_init(post_init)
        .build()
    )
    
    # Add database session to all handlers
    from functools import wraps
    
    # Register handlers
    moderation_handlers = get_moderation_handlers()
    protection_handlers = get_protection_handlers()
    
    # Add callback handler
    application.add_handler(CallbackQueryHandler(callback_handler))
    
    # Add all other handlers
    for handler in moderation_handlers + protection_handlers:
        application.add_handler(handler)
    
    # Add error handler
    application.add_error_handler(error_handler)
    
    # Start the bot
    logger.info("Bot started successfully!")
    print("✅ Bot is running! Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
