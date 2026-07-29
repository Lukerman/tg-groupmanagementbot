import logging
from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ChatMemberHandler,
    filters,
    ContextTypes
)
from src.configs.settings import BOT_TOKEN, ADMIN_ID, COLOR_THEMES
from src.models.database import get_session, GroupSettings

# Import handlers
from src.handlers.admin import settings_command, theme_command, set_welcome, set_goodbye, locks_command
from src.handlers.moderation import ban_user, mute_user, unmute_user, warn_user, kick_user, purge_messages
from src.handlers.protection import check_protection, anti_spam_check
from src.handlers.welcome import on_new_member, on_member_left, verify_captcha
from src.handlers.filters import add_filter, list_filters, remove_filter, check_filter_response
from src.handlers.notes import add_note, list_notes, view_note, remove_note
from src.handlers.inline import handle_callback

# Setup logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send welcome message with bot info"""
    await update.effective_message.reply_text(
        "🤖 **Advanced Group Management Bot**\n\n"
        "✨ Features:\n"
        "• 🎨 8 Color Themes with inline buttons\n"
        "• 🛡️ Advanced protection system\n"
        "• 👋 Custom welcome/goodbye messages\n"
        "• ⚠️ Full moderation suite (ban, mute, warn)\n"
        "• 📝 Filters and notes\n"
        "• 🔒 Permission controls\n\n"
        "Commands:\n"
        "/settings - Open themed settings panel\n"
        "/theme - Change color theme\n"
        "/ban, /mute, /warn, /kick - Moderation\n"
        "/setwelcome, /setgoodbye - Custom messages\n"
        "/filter, /note - Create filters/notes\n"
        "/lock, /unlock - Chat permissions",
        parse_mode="HTML"
    )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Send help message"""
    await update.effective_message.reply_text(
        "📖 **Help & Commands**\n\n"
        "**Admin Commands:**\n"
        "/settings - Themed settings panel\n"
        "/theme - Change emoji theme\n"
        "/ban [user] - Ban user\n"
        "/mute [user] [time] - Mute user\n"
        "/unmute [user] - Unmute user\n"
        "/warn [user] - Warn user\n"
        "/kick [user] - Kick user\n"
        "/purge - Delete messages\n"
        "/setwelcome <msg> - Set welcome\n"
        "/setgoodbye <msg> - Set goodbye\n"
        "/filter <k|v> - Add filter\n"
        "/filters - List filters\n"
        "/note <n|c> - Add note\n"
        "/notes - List notes\n"
        "/lock/unlock - Permissions\n\n"
        "**Themes:** " + ", ".join([t.capitalize() for t in COLOR_THEMES.keys()]),
        parse_mode="HTML"
    )

async def post_init(application: Application):
    """Initialize bot after startup"""
    logger.info("Bot initialized successfully!")
    
    # Store admin ID in bot data
    application.bot_data['admin_id'] = ADMIN_ID
    logger.info(f"Admin ID set to: {ADMIN_ID}")

def main():
    """Main function to run the bot"""
    logger.info("Starting Advanced Group Management Bot...")
    
    # Create application
    application = Application.builder().token(BOT_TOKEN).post_init(post_init).build()
    
    # Command handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("settings", settings_command))
    application.add_handler(CommandHandler("theme", theme_command))
    application.add_handler(CommandHandler("setwelcome", set_welcome))
    application.add_handler(CommandHandler("setgoodbye", set_goodbye))
    application.add_handler(CommandHandler("lock", locks_command))
    application.add_handler(CommandHandler("unlock", locks_command))
    
    # Moderation commands
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("mute", mute_user))
    application.add_handler(CommandHandler("unmute", unmute_user))
    application.add_handler(CommandHandler("warn", warn_user))
    application.add_handler(CommandHandler("kick", kick_user))
    application.add_handler(CommandHandler("purge", purge_messages))
    
    # Filter commands
    application.add_handler(CommandHandler("filter", add_filter))
    application.add_handler(CommandHandler("filters", list_filters))
    application.add_handler(CommandHandler("removefilter", remove_filter))
    
    # Note commands
    application.add_handler(CommandHandler("note", add_note))
    application.add_handler(CommandHandler("notes", list_notes))
    application.add_handler(CommandHandler("viewnote", view_note))
    application.add_handler(CommandHandler("removenote", remove_note))
    
    # Message handlers (protection, filters)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_filter_response))
    application.add_handler(MessageHandler(filters.ALL, check_protection))
    
    # Chat member handlers (welcome/goodbye)
    application.add_handler(ChatMemberHandler(on_new_member, ChatMemberHandler.CHAT_MEMBER))
    
    # Callback query handler (inline buttons)
    application.add_handler(CallbackQueryHandler(handle_callback))
    
    # Run the bot
    logger.info("Bot is running... Press Ctrl+C to stop.")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == '__main__':
    main()
