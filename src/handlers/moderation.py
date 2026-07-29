from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from src.models.database import get_session, GroupSettings, UserWarnings
from src.utils.helpers import is_admin, parse_time

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if admin
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        await update.effective_message.reply_text("❌ Only admins can use this command.")
        return
    
    # Get target user from args or reply
    if update.effective_message and update.effective_message.reply_to_message:
        target_user = update.effective_message.reply_to_message.from_user
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_user = await context.bot.get_chat(target_id)
        except (ValueError, Exception):
            await update.effective_message.reply_text("❌ Invalid user ID")
            return
    else:
        await update.effective_message.reply_text("📝 Reply to a user or provide user ID")
        return
    
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    try:
        await chat.ban(target_user.id)
        await update.effective_message.reply_text(
            f"🔨 {target_user.mention_html()} has been banned.\nReason: {reason}",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Failed to ban: {str(e)}")

async def mute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user in the group"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if admin
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        await update.effective_message.reply_text("❌ Only admins can use this command.")
        return
    
    # Get target user
    if update.effective_message and update.effective_message.reply_to_message:
        target_user = update.effective_message.reply_to_message.from_user
        duration = None
    elif context.args:
        try:
            if len(context.args) >= 2 and parse_time(context.args[1]):
                target_id = int(context.args[0])
                duration = parse_time(context.args[1])
                target_user = await context.bot.get_chat(target_id)
            else:
                target_id = int(context.args[0])
                target_user = await context.bot.get_chat(target_id)
                duration = None
        except (ValueError, Exception):
            await update.effective_message.reply_text("❌ Invalid user ID or time format")
            return
    else:
        await update.effective_message.reply_text("📝 Reply to a user or provide user ID [duration]")
        return
    
    import time
    try:
        if duration:
            until = int(time.time()) + duration
            await chat.restrict_member(
                target_user.id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=until
            )
            await update.effective_message.reply_text(
                f"🔇 {target_user.mention_html()} has been muted for {context.args[1]}.",
                parse_mode="HTML"
            )
        else:
            await chat.restrict_member(
                target_user.id,
                permissions=ChatPermissions(can_send_messages=False)
            )
            await update.effective_message.reply_text(
                f"🔇 {target_user.mention_html()} has been muted.",
                parse_mode="HTML"
            )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Failed to mute: {str(e)}")

async def unmute_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Unmute a user in the group"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if admin
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        await update.effective_message.reply_text("❌ Only admins can use this command.")
        return
    
    # Get target user
    if update.effective_message and update.effective_message.reply_to_message:
        target_user = update.effective_message.reply_to_message.from_user
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_user = await context.bot.get_chat(target_id)
        except (ValueError, Exception):
            await update.effective_message.reply_text("❌ Invalid user ID")
            return
    else:
        await update.effective_message.reply_text("📝 Reply to a user or provide user ID")
        return
    
    try:
        await chat.restrict_member(
            target_user.id,
            permissions=ChatPermissions(
                can_send_messages=True,
                can_send_media_messages=True,
                can_send_other_messages=True,
                can_add_web_page_previews=True
            )
        )
        await update.effective_message.reply_text(
            f"🔊 {target_user.mention_html()} has been unmuted.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Failed to unmute: {str(e)}")

async def warn_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if admin
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        await update.effective_message.reply_text("❌ Only admins can use this command.")
        return
    
    # Get target user
    if update.effective_message and update.effective_message.reply_to_message:
        target_user = update.effective_message.reply_to_message.from_user
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_user = await context.bot.get_chat(target_id)
        except (ValueError, Exception):
            await update.effective_message.reply_text("❌ Invalid user ID")
            return
    else:
        await update.effective_message.reply_text("📝 Reply to a user or provide user ID")
        return
    
    reason = " ".join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    db = get_session()
    try:
        warning = db.query(UserWarnings).filter_by(
            chat_id=chat.id,
            user_id=target_user.id
        ).first()
        
        if not warning:
            warning = UserWarnings(chat_id=chat.id, user_id=target_user.id, warnings=0)
            db.add(warning)
        
        warning.warnings += 1
        warning.reason = reason
        db.commit()
        
        settings = db.query(GroupSettings).filter_by(chat_id=chat.id).first()
        warn_limit = settings.warn_limit if settings else 3
        
        if warning.warnings >= warn_limit:
            await chat.ban(target_user.id)
            await update.effective_message.reply_text(
                f"⚠️ {target_user.mention_html()} has been banned after {warning.warnings} warnings.",
                parse_mode="HTML"
            )
            db.delete(warning)
            db.commit()
        else:
            await update.effective_message.reply_text(
                f"⚠️ {target_user.mention_html()} warned ({warning.warnings}/{warn_limit}).\nReason: {reason}",
                parse_mode="HTML"
            )
    finally:
        db.close()

async def kick_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the group"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if admin
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        await update.effective_message.reply_text("❌ Only admins can use this command.")
        return
    
    # Get target user
    if update.effective_message and update.effective_message.reply_to_message:
        target_user = update.effective_message.reply_to_message.from_user
    elif context.args:
        try:
            target_id = int(context.args[0])
            target_user = await context.bot.get_chat(target_id)
        except (ValueError, Exception):
            await update.effective_message.reply_text("❌ Invalid user ID")
            return
    else:
        await update.effective_message.reply_text("📝 Reply to a user or provide user ID")
        return
    
    try:
        await chat.kick_member(target_user.id)
        await update.effective_message.reply_text(
            f"👢 {target_user.mention_html()} has been kicked.",
            parse_mode="HTML"
        )
    except Exception as e:
        await update.effective_message.reply_text(f"❌ Failed to kick: {str(e)}")

async def purge_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Purge messages (reply to start point)"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    user = update.effective_user
    
    # Check if admin
    admins = await chat.get_administrators()
    if not is_admin(user.id, admins) and user.id != context.bot_data.get('admin_id'):
        await update.effective_message.reply_text("❌ Only admins can use this command.")
        return
    
    if not update.effective_message or not update.effective_message.reply_to_message:
        await update.effective_message.reply_text("📝 Reply to the message where purge should start")
        return
    
    start_msg_id = update.effective_message.reply_to_message.message_id
    end_msg_id = update.effective_message.message_id
    
    deleted = 0
    for msg_id in range(start_msg_id, end_msg_id + 1):
        try:
            await context.bot.delete_message(chat_id=chat.id, message_id=msg_id)
            deleted += 1
        except:
            pass
    
    await update.effective_message.reply_text(f"🗑️ Purged {deleted} messages.")
