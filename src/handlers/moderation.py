from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from sqlalchemy.orm import Session
import sys
sys.path.append('..')
from src.db_operations import (
    get_group, update_group_settings, create_or_update_user, 
    add_warning, get_warnings, clear_warnings, mute_user, unmute_user,
    ban_user, unban_user, is_banned, is_muted, log_action, set_group_setting, get_group_setting
)
from src.handlers.permissions import check_admin, check_bot_admin, check_permissions
from src.utils.helpers import mention_user, format_time, parse_time
from src.utils.keyboards import get_moderation_keyboard, get_warning_keyboard

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command"""
    user = update.effective_user
    chat = update.effective_chat
    
    if chat and chat.type != 'private':
        # Bot added to group
        await update_group_settings(context.db_session, chat.id, title=chat.title)
        await update.message.reply_text(
            f"👋 Hello! I've been added to {chat.title}!\n\n"
            f"Make me an admin to use my moderation features.\n"
            f"Use /help to see all available commands.",
            parse_mode='Markdown'
        )
    else:
        # Private chat
        await update.message.reply_text(
            f"👋 Hello {user.first_name}!\n\n"
            f"I'm a powerful group management bot with advanced features:\n"
            f"• Welcome messages & CAPTCHA\n"
            f"• Anti-spam & Anti-flood\n"
            f"• Warnings, Mutes & Bans\n"
            f"• Link protection\n"
            f"• And much more!\n\n"
            f"Add me to your group to get started!",
            parse_mode='Markdown'
        )

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command"""
    help_text = """
📖 **Help - Available Commands**

**General:**
/start - Start the bot
/help - Show this help message
/settings - Group settings (admins only)

**Moderation (Admins):**
/ban - Ban a user
/unban - Unban a user
/mute - Mute a user
/unmute - Unmute a user
/warn - Warn a user
/warnings - View warnings
/clearwarnings - Clear all warnings
/kick - Kick a user
/purge - Delete messages

**Settings (Admins):**
/welcome - Set welcome message
/captcha - Enable/disable captcha
/antispam - Configure anti-spam
/antiflood - Configure anti-flood
/bannedwords - Manage banned words
/linkprotect - Toggle link protection

**Info:**
/info - Get user/group info
/ping - Check bot status
"""
    await update.message.reply_text(help_text, parse_mode='Markdown')

async def settings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /settings command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        await update.message.reply_text("This command only works in groups!")
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    group = get_group(context.db_session, chat.id)
    
    settings_text = f"⚙️ **Group Settings for {chat.title}**\n\n"
    settings_text += f"👋 Welcome: {'✅ Enabled' if group and group.welcome_enabled else '❌ Disabled'}\n"
    settings_text += f"🤖 Captcha: {'✅ Enabled' if group and group.captcha_enabled else '❌ Disabled'}\n"
    settings_text += f"🛡️ Anti-Spam: {'✅ Enabled' if group and group.anti_spam_enabled else '❌ Disabled'}\n"
    settings_text += f"💬 Anti-Flood: {'✅ Enabled' if group and group.antiflood_limit else '❌ Disabled'}\n"
    
    keyboard = get_moderation_keyboard(chat.id)
    await update.message.reply_text(settings_text, parse_mode='Markdown', reply_markup=keyboard)

async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ban command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not await check_permissions(update, context, can_restrict=True):
        await update.message.reply_text("❌ Bot needs restrict members permission!")
        return
    
    # Get target user
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        await update.message.reply_text("❌ Please reply to a user or provide user ID!")
        return
    
    # Get reason
    reason = ' '.join(context.args[1:]) if context.args else "No reason provided"
    
    # Check if already banned
    if is_banned(context.db_session, target_user.id, chat.id):
        await update.message.reply_text(f"❌ {target_user.first_name} is already banned!")
        return
    
    # Ban user
    try:
        await chat.ban_member(target_user.id)
        ban_user(context.db_session, target_user.id, chat.id, user.id, reason)
        log_action(context.db_session, chat.id, target_user.id, "BAN", f"Banned by {user.first_name}: {reason}")
        
        await update.message.reply_text(
            f"🚫 **Banned!**\n"
            f"User: {mention_user(target_user.id, target_user.first_name)}\n"
            f"Reason: {reason}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to ban: {str(e)}")

async def unban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unban command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not await check_permissions(update, context, can_restrict=True):
        await update.message.reply_text("❌ Bot needs restrict members permission!")
        return
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        await update.message.reply_text("❌ Please reply to a user or provide user ID!")
        return
    
    try:
        await chat.unban_member(target_user.id)
        unban_user(context.db_session, target_user.id, chat.id)
        log_action(context.db_session, chat.id, target_user.id, "UNBAN", f"Unbanned by {user.first_name}")
        
        await update.message.reply_text(
            f"✅ **Unbanned!**\n"
            f"User: {mention_user(target_user.id, target_user.first_name)}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to unban: {str(e)}")

async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /mute command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not await check_permissions(update, context, can_restrict=True):
        await update.message.reply_text("❌ Bot needs restrict members permission!")
        return
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        await update.message.reply_text("❌ Please reply to a user or provide user ID!")
        return
    
    # Parse duration
    duration = None
    reason = "No reason provided"
    
    if context.args:
        for arg in context.args:
            seconds = parse_time(arg)
            if seconds > 0:
                duration = seconds
            else:
                reason = ' '.join([a for a in context.args if not a[0].isdigit()])
                break
    
    try:
        permissions = ChatPermissions(
            can_send_messages=False,
            can_send_audios=False,
            can_send_documents=False,
            can_send_photos=False,
            can_send_videos=False,
            can_send_video_notes=False,
            can_send_voice_notes=False,
            can_send_polls=False,
            can_send_other_messages=False,
            can_add_web_page_previews=False,
            can_change_info=False,
            can_invite_users=False,
            can_pin_messages=False
        )
        
        if duration:
            await chat.restrict_member(target_user.id, permissions, until_date=context.bot.date + timedelta(seconds=duration))
            mute_user(context.db_session, target_user.id, chat.id, user.id, duration, reason)
            time_str = format_time(duration)
            msg = f"🔇 **Muted for {time_str}!**\n"
        else:
            await chat.restrict_member(target_user.id, permissions)
            mute_user(context.db_session, target_user.id, chat.id, user.id, None, reason)
            msg = "🔇 **Muted permanently!**\n"
        
        msg += f"User: {mention_user(target_user.id, target_user.first_name)}\nReason: {reason}"
        
        log_action(context.db_session, chat.id, target_user.id, "MUTE", f"Muted by {user.first_name}")
        await update.message.reply_text(msg, parse_mode='Markdown')
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to mute: {str(e)}")

async def unmute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /unmute command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not await check_permissions(update, context, can_restrict=True):
        await update.message.reply_text("❌ Bot needs restrict members permission!")
        return
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        await update.message.reply_text("❌ Please reply to a user or provide user ID!")
        return
    
    try:
        await chat.restrict_member(
            target_user.id,
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
        unmute_user(context.db_session, target_user.id, chat.id)
        log_action(context.db_session, chat.id, target_user.id, "UNMUTE", f"Unmuted by {user.first_name}")
        
        await update.message.reply_text(
            f"🔊 **Unmuted!**\n"
            f"User: {mention_user(target_user.id, target_user.first_name)}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to unmute: {str(e)}")

async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /warn command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        await update.message.reply_text("❌ Please reply to a user or provide user ID!")
        return
    
    reason = ' '.join(context.args[1:]) if context.args else "No reason provided"
    
    warning_count = add_warning(context.db_session, target_user.id, chat.id, reason, user.id)
    log_action(context.db_session, chat.id, target_user.id, "WARN", f"Warned by {user.first_name}: {reason}")
    
    await update.message.reply_text(
        f"⚠️ **User Warned!**\n"
        f"User: {mention_user(target_user.id, target_user.first_name)}\n"
        f"Reason: {reason}\n"
        f"Warnings: {warning_count}/3",
        parse_mode='Markdown'
    )
    
    # Auto-ban after 3 warnings
    if warning_count >= 3:
        try:
            await chat.ban_member(target_user.id)
            await update.message.reply_text(
                f"🚫 **Auto-Banned!**\n"
                f"{mention_user(target_user.id, target_user.first_name)} reached 3 warnings!",
                parse_mode='Markdown'
            )
        except Exception:
            pass

async def warnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /warnings command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        target_user = user
    
    warnings = get_warnings(context.db_session, target_user.id, chat.id)
    
    if not warnings:
        await update.message.reply_text(f"✅ {target_user.first_name} has no warnings!")
        return
    
    text = f"⚠️ **Warnings for {target_user.first_name}**\n\n"
    for i, w in enumerate(warnings, 1):
        text += f"{i}. {w.reason} (by {w.warned_by})\n"
    
    keyboard = get_warning_keyboard(target_user.id, chat.id)
    await update.message.reply_text(text, parse_mode='Markdown', reply_markup=keyboard)

async def clearwarnings_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /clearwarnings command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        await update.message.reply_text("❌ Please reply to a user or provide user ID!")
        return
    
    count = clear_warnings(context.db_session, target_user.id, chat.id)
    log_action(context.db_session, chat.id, target_user.id, "CLEAR_WARNINGS", f"Cleared by {user.first_name}")
    
    await update.message.reply_text(
        f"✅ **Warnings Cleared!**\n"
        f"User: {mention_user(target_user.id, target_user.first_name)}\n"
        f"Cleared: {count} warnings",
        parse_mode='Markdown'
    )

async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /kick command"""
    chat = update.effective_chat
    user = update.effective_user
    
    if not chat or chat.type == 'private':
        return
    
    if not await check_admin(update, context, context.db_session):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not await check_permissions(update, context, can_restrict=True):
        await update.message.reply_text("❌ Bot needs restrict members permission!")
        return
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        await update.message.reply_text("❌ Please reply to a user or provide user ID!")
        return
    
    try:
        await chat.ban_member(target_user.id)
        await chat.unban_member(target_user.id)
        log_action(context.db_session, chat.id, target_user.id, "KICK", f"Kicked by {user.first_name}")
        
        await update.message.reply_text(
            f"👢 **Kicked!**\n"
            f"User: {mention_user(target_user.id, target_user.first_name)}",
            parse_mode='Markdown'
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to kick: {str(e)}")

async def info_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /info command"""
    chat = update.effective_chat
    
    if update.message.reply_to_message:
        target_user = update.message.reply_to_message.from_user
    elif context.args:
        try:
            user_id = int(context.args[0])
            target_user = await context.bot.get_chat(user_id)
        except (ValueError, Exception):
            await update.message.reply_text("❌ Invalid user ID!")
            return
    else:
        target_user = update.effective_user
    
    is_user_banned = is_banned(context.db_session, target_user.id, chat.id) if chat else False
    is_user_muted = is_muted(context.db_session, target_user.id, chat.id) if chat else False
    warnings = get_warnings(context.db_session, target_user.id, chat.id) if chat else []
    
    status = "🚫 Banned" if is_user_banned else ("🔇 Muted" if is_user_muted else "✅ Active")
    
    info_text = f"📊 **User Info**\n\n"
    info_text += f"👤 Name: {target_user.first_name}"
    if target_user.last_name:
        info_text += f" {target_user.last_name}"
    info_text += f"\n🆔 ID: <code>{target_user.id}</code>\n"
    if target_user.username:
        info_text += f"📝 Username: @{target_user.username}\n"
    info_text += f"📌 Status: {status}\n"
    info_text += f"⚠️ Warnings: {len(warnings)}"
    
    await update.message.reply_text(info_text, parse_mode='HTML')

async def ping_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /ping command"""
    import time
    start = time.time()
    msg = await update.message.reply_text("🏓 Pong!")
    end = time.time()
    await msg.edit_text(f"🏓 Pong! `{int((end - start) * 1000)}ms`", parse_mode='Markdown')

def get_moderation_handlers():
    """Get all moderation command handlers"""
    from datetime import timedelta
    
    return [
        CommandHandler('start', start_command),
        CommandHandler('help', help_command),
        CommandHandler('settings', settings_command),
        CommandHandler('ban', ban_command),
        CommandHandler('unban', unban_command),
        CommandHandler('mute', mute_command),
        CommandHandler('unmute', unmute_command),
        CommandHandler('warn', warn_command),
        CommandHandler('warnings', warnings_command),
        CommandHandler('clearwarnings', clearwarnings_command),
        CommandHandler('kick', kick_command),
        CommandHandler('info', info_command),
        CommandHandler('ping', ping_command),
    ]
