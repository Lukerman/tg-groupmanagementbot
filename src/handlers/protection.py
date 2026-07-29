from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes
import sys
sys.path.append('..')
from src.db_operations import (
    get_group, update_group_settings, create_or_update_user,
    create_captcha_session, get_captcha_session, verify_captcha,
    set_group_setting, get_group_setting, log_action, is_muted
)
from src.handlers.permissions import check_admin, check_bot_admin
from src.utils.helpers import generate_math_captcha, mention_user
from src.utils.keyboards import get_captcha_keyboard

# Track message timestamps for anti-flood
user_messages = {}

async def welcome_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the group"""
    chat = update.effective_chat
    
    if not chat or chat.type in ['private', 'channel']:
        return
    
    group = get_group(context.db_session, chat.id)
    if not group or not group.welcome_enabled:
        return
    
    # Check if bot is admin
    if not await check_bot_admin(update, context):
        return
    
    for user in update.message.new_chat_members:
        if user.is_bot:
            continue
        
        # Create or update user in DB
        create_or_update_user(
            context.db_session,
            user.id,
            user.username,
            user.first_name,
            user.last_name,
            user.is_premium,
            user.language_code
        )
        
        # Send welcome message
        welcome_msg = group.welcome_message or f"👋 Welcome {mention_user(user.id, user.first_name)} to {chat.title}!"
        welcome_msg = welcome_msg.replace('{name}', user.first_name).replace('{title}', chat.title)
        
        if group.captcha_enabled:
            # Generate captcha
            question, answer = generate_math_captcha()
            session = create_captcha_session(context.db_session, user.id, chat.id, answer)
            
            keyboard = get_captcha_keyboard(user.id, answer)
            
            msg = await update.message.reply_text(
                f"🤖 **CAPTCHA Required**\n\n"
                f"{mention_user(user.id, user.first_name)}, please solve:\n\n"
                f"**{question}**\n\n"
                f"You have 5 minutes to verify.",
                parse_mode='Markdown',
                reply_markup=keyboard
            )
            
            # Mute user until verified
            try:
                permissions = ChatPermissions(can_send_messages=False)
                await chat.restrict_member(user.id, permissions)
            except Exception:
                pass
        else:
            await update.message.reply_text(welcome_msg, parse_mode='Markdown')
        
        log_action(context.db_session, chat.id, user.id, "JOIN", "New member joined")

async def captcha_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle captcha button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data.split('_')
    if data[0] != 'captcha':
        return
    
    user_id = int(data[1])
    answer = int(data[2])
    
    if query.from_user.id != user_id:
        await query.edit_message_text("❌ This captcha is not for you!")
        return
    
    session = get_captcha_session(context.db_session, user_id, query.message.chat.id)
    if not session:
        await query.edit_message_text("❌ Captcha session expired!")
        return
    
    if str(answer) == session.answer:
        # Verify and unmute
        verify_captcha(context.db_session, session.id)
        
        try:
            await query.message.chat.restrict_member(
                user_id,
                ChatPermissions(
                    can_send_messages=True,
                    can_send_audios=True,
                    can_send_documents=True,
                    can_send_photos=True,
                    can_send_videos=True,
                    can_send_video_notes=True,
                    can_send_voice_notes=True,
                    can_send_polls=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                    can_invite_users=True
                )
            )
        except Exception:
            pass
        
        await query.edit_message_text(f"✅ **Verified!** Welcome to the group!", parse_mode='Markdown')
        log_action(context.db_session, query.message.chat.id, user_id, "CAPTCHA_PASS", "User passed captcha")
    else:
        await query.edit_message_text("❌ **Wrong answer!** You've been kicked.", parse_mode='Markdown')
        try:
            await query.message.chat.ban_member(user_id)
            await query.message.chat.unban_member(user_id)
        except Exception:
            pass
        log_action(context.db_session, query.message.chat.id, user_id, "CAPTCHA_FAIL", "User failed captcha")

async def antiflood_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Anti-flood handler"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type in ['private', 'channel'] or user.is_bot:
        return
    
    group = get_group(context.db_session, chat.id)
    if not group or not group.antiflood_limit:
        return
    
    # Skip admins
    if await check_admin(update, context, context.db_session):
        return
    
    now = context.bot.date.timestamp()
    limit = group.antiflood_limit
    window = group.antiflood_window or 10
    
    key = f"{user.id}_{chat.id}"
    
    if key not in user_messages:
        user_messages[key] = []
    
    # Clean old messages
    user_messages[key] = [t for t in user_messages[key] if now - t < window]
    user_messages[key].append(now)
    
    if len(user_messages[key]) > limit:
        # Flood detected - mute for 1 minute
        try:
            permissions = ChatPermissions(can_send_messages=False)
            await chat.restrict_member(user.id, permissions, until_date=context.bot.date + timedelta(seconds=60))
            await update.message.delete()
            
            await update.message.reply_text(
                f"⚠️ **Flood detected!**\n"
                f"{mention_user(user.id, user.first_name)} has been muted for 1 minute.",
                parse_mode='Markdown'
            )
            log_action(context.db_session, chat.id, user.id, "ANTIFLOOD", "User flooded")
        except Exception:
            pass

async def link_protection_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages with links if protection is enabled"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type in ['private', 'channel'] or user.is_bot:
        return
    
    if not update.message.text:
        return
    
    # Skip admins
    if await check_admin(update, context, context.db_session):
        return
    
    link_protect = get_group_setting(context.db_session, chat.id, 'link_protect')
    if link_protect != 'true':
        return
    
    # Check for links
    import re
    url_pattern = r'https?://[^\s<>"]+|www\.[^\s<>"]+|t\.me/[^\s<>"]+'
    if re.search(url_pattern, update.message.text):
        try:
            await update.message.delete()
            await update.message.reply_text(
                f"⚠️ {mention_user(user.id, user.first_name)}, links are not allowed in this group!",
                parse_mode='Markdown'
            )
            log_action(context.db_session, chat.id, user.id, "LINK_DELETE", "Deleted link message")
        except Exception:
            pass

async def banned_words_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages containing banned words"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type in ['private', 'channel'] or user.is_bot:
        return
    
    if not update.message.text:
        return
    
    # Skip admins
    if await check_admin(update, context, context.db_session):
        return
    
    banned_words_str = get_group_setting(context.db_session, chat.id, 'banned_words')
    if not banned_words_str:
        return
    
    import json
    try:
        banned_words = json.loads(banned_words_str)
    except:
        banned_words = []
    
    text_lower = update.message.text.lower()
    for word in banned_words:
        if word.lower() in text_lower:
            try:
                await update.message.delete()
                await update.message.reply_text(
                    f"⚠️ {mention_user(user.id, user.first_name)}, that word is not allowed!",
                    parse_mode='Markdown'
                )
                log_action(context.db_session, chat.id, user.id, "BANNED_WORD", f"Banned word: {word}")
            except Exception:
                pass
            break

async def welcome_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set welcome message"""
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text("This command only works in groups!")
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if context.args:
        message = ' '.join(context.args)
        update_group_settings(context.db_session, chat.id, welcome_enabled=True, welcome_message=message)
        await update.message.reply_text(f"✅ Welcome message set!\n\n{message}")
    else:
        current = get_group(context.db_session, chat.id)
        status = "Enabled" if current and current.welcome_enabled else "Disabled"
        msg = current.welcome_message if current and current.welcome_message else "No message set"
        await update.message.reply_text(
            f"👋 **Welcome Settings**\n\n"
            f"Status: {status}\n"
            f"Message: {msg}\n\n"
            f"Use /welcome <message> to set. Available: {{name}}, {{title}}",
            parse_mode='Markdown'
        )

async def captcha_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle captcha"""
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text("This command only works in groups!")
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    group = get_group(context.db_session, chat.id)
    new_state = not (group and group.captcha_enabled)
    update_group_settings(context.db_session, chat.id, captcha_enabled=new_state)
    
    await update.message.reply_text(f"🤖 CAPTCHA {'enabled' if new_state else 'disabled'}!")

async def antiflood_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Set anti-flood settings"""
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text("This command only works in groups!")
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if context.args and context.args[0].isdigit():
        limit = int(context.args[0])
        window = int(context.args[1]) if len(context.args) > 1 else 10
        update_group_settings(context.db_session, chat.id, antiflood_limit=limit, antiflood_window=window)
        await update.message.reply_text(f"✅ Anti-flood set to {limit} messages per {window} seconds!")
    else:
        group = get_group(context.db_session, chat.id)
        limit = group.antiflood_limit if group and group.antiflood_limit else 0
        await update.message.reply_text(
            f"💬 **Anti-Flood Settings**\n\n"
            f"Current: {limit} messages\n"
            f"Use /antiflood <count> [window_seconds]\n"
            f"Example: /antiflood 5 10",
            parse_mode='Markdown'
        )

async def linkprotect_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Toggle link protection"""
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text("This command only works in groups!")
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    current = get_group_setting(context.db_session, chat.id, 'link_protect')
    new_value = 'false' if current == 'true' else 'true'
    set_group_setting(context.db_session, chat.id, 'link_protect', new_value)
    
    await update.message.reply_text(f"🔗 Link protection {'enabled' if new_value == 'true' else 'disabled'}!")

async def bannedwords_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Manage banned words"""
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        await update.message.reply_text("This command only works in groups!")
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    import json
    
    if not context.args:
        current = get_group_setting(context.db_session, chat.id, 'banned_words')
        words = json.loads(current) if current else []
        await update.message.reply_text(
            f"🚫 **Banned Words**\n\n"
            f"Current: {', '.join(words) if words else 'None'}\n\n"
            f"Use:\n"
            f"/bannedwords add <word>\n"
            f"/bannedwords remove <word>\n"
            f"/bannedwords clear",
            parse_mode='Markdown'
        )
        return
    
    action = context.args[0]
    current = get_group_setting(context.db_session, chat.id, 'banned_words')
    words = json.loads(current) if current else []
    
    if action == 'add' and len(context.args) > 1:
        word = context.args[1]
        if word not in words:
            words.append(word)
            set_group_setting(context.db_session, chat.id, 'banned_words', json.dumps(words))
            await update.message.reply_text(f"✅ Added '{word}' to banned words!")
    elif action == 'remove' and len(context.args) > 1:
        word = context.args[1]
        if word in words:
            words.remove(word)
            set_group_setting(context.db_session, chat.id, 'banned_words', json.dumps(words))
            await update.message.reply_text(f"✅ Removed '{word}' from banned words!")
    elif action == 'clear':
        set_group_setting(context.db_session, chat.id, 'banned_words', '[]')
        await update.message.reply_text("✅ Cleared all banned words!")

def get_protection_handlers():
    """Get all protection handlers"""
    from datetime import timedelta
    
    return [
        CommandHandler('welcome', welcome_command),
        CommandHandler('captcha', captcha_command),
        CommandHandler('antiflood', antiflood_command),
        CommandHandler('linkprotect', linkprotect_command),
        CommandHandler('bannedwords', bannedwords_command),
        MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, welcome_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, antiflood_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, link_protection_handler),
        MessageHandler(filters.TEXT & ~filters.COMMAND, banned_words_handler),
        CallbackQueryHandler(captcha_callback_handler, pattern='^captcha_'),
    ]
