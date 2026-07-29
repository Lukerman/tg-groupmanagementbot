"""Moderation Handlers - Ban, Mute, Warn, Kick"""
from telegram import Update, ChatPermissions
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from sqlalchemy import select
from datetime import datetime

from src.models.database import ChatSettings, User, Warning, AdminRole
from src.utils.helpers import check_user_admin, extract_time, format_time, mention_html
from src.utils.inline_keyboards import get_moderation_actions_keyboard, get_warnings_keyboard


async def ban_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Ban a user from the group"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    # Get target user
    if not context.args or not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "<code>/ban</code> (reply to message)\n"
            "<code>/ban @username</code>\n"
            "<code>/ban user_id</code>",
            parse_mode='HTML'
        )
        return
    
    # Get target user ID
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args[0].startswith('@'):
        # Try to resolve username (simplified)
        await update.message.reply_text("Please reply to the user's message for accurate banning.")
        return
    else:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
    
    # Get reason
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.chat_id,
            user_id=target_id,
            until_date=None  # Permanent ban
        )
        
        target_name = f"User {target_id}"
        if update.message.reply_to_message:
            target_name = mention_html(update.message.reply_to_message.from_user)
        
        await update.message.reply_html(
            f"🚫 <b>Banned!</b>\n\n"
            f"{target_name} has been banned.\n"
            f"<b>Reason:</b> <i>{reason}</i>",
            reply_markup=get_moderation_actions_keyboard(target_id) if context.args and context.args[0] == "inline" else None
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to ban user.\nError: {e}")


async def mute_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Mute a user"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not context.args and not update.message.reply_to_message:
        await update.message.reply_text(
            "⚠️ <b>Usage:</b>\n"
            "<code>/mute</code> (reply to message)\n"
            "<code>/mute 10m</code> (for 10 minutes)\n"
            "<code>/mute 2h</code> (for 2 hours)",
            parse_mode='HTML'
        )
        return
    
    target_id = None
    duration = None
    
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
        if context.args:
            duration = extract_time(context.args[0])
    elif context.args:
        if len(context.args) >= 2:
            try:
                target_id = int(context.args[0])
            except ValueError:
                await update.message.reply_text("❌ Invalid user ID!")
                return
            duration = extract_time(context.args[1])
        else:
            # Maybe just a duration, assume replied user
            duration = extract_time(context.args[0])
            if update.message.reply_to_message:
                target_id = update.message.reply_to_message.from_user.id
    
    if not target_id:
        await update.message.reply_text("❌ Please specify a user or reply to their message!")
        return
    
    try:
        await context.bot.restrict_chat_member(
            chat_id=update.chat_id,
            user_id=target_id,
            permissions=ChatPermissions(
                can_send_messages=False,
                can_send_media_messages=False,
                can_send_other_messages=False,
                can_add_web_page_previews=False,
            ),
            until_date=duration
        )
        
        target_name = f"User {target_id}"
        if update.message.reply_to_message:
            target_name = mention_html(update.message.reply_to_message.from_user)
        
        time_text = f" for {format_time(duration)}" if duration else ""
        await update.message.reply_html(f"🔇 <b>Muted!</b>\n\n{target_name} has been muted{time_text}.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to mute user.\nError: {e}")


async def warn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Warn a user"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text("❌ Reply to a user's message or provide user ID!")
        return
    
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
    
    reason = ' '.join(context.args[1:]) if len(context.args) > 1 else "No reason provided"
    
    async with context.bot_data['db_session']() as session:
        # Add warning
        warning = Warning(
            chat_id=update.chat_id,
            user_id=target_id,
            reason=reason,
            warned_by=user.id
        )
        session.add(warning)
        
        # Count warnings
        result = await session.execute(
            select(Warning).where(
                Warning.chat_id == update.chat_id,
                Warning.user_id == target_id
            )
        )
        warnings = result.scalars().all()
        warning_count = len(warnings)
        
        max_warnings = 3  # Configurable
        
        text = f"⚠️ <b>Warning!</b>\n\n"
        text += f"{mention_html(update.message.reply_to_message.from_user) if update.message.reply_to_message else f'User {target_id}'} has been warned.\n"
        text += f"<b>Reason:</b> <i>{reason}</i>\n"
        text += f"<b>Warnings:</b> {warning_count}/{max_warnings}"
        
        if warning_count >= max_warnings:
            # Auto-ban
            try:
                await context.bot.ban_chat_member(chat_id=update.chat_id, user_id=target_id)
                text += "\n\n🚫 <b>Auto-banned!</b> (Max warnings reached)"
            except Exception:
                pass
        
        await session.commit()
        await update.message.reply_html(text, reply_markup=get_warnings_keyboard(target_id, warning_count, max_warnings))


async def kick_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Kick a user from the group"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not update.message.reply_to_message and not context.args:
        await update.message.reply_text("❌ Reply to a user's message or provide user ID!")
        return
    
    target_id = None
    if update.message.reply_to_message:
        target_id = update.message.reply_to_message.from_user.id
    elif context.args:
        try:
            target_id = int(context.args[0])
        except ValueError:
            await update.message.reply_text("❌ Invalid user ID!")
            return
    
    try:
        await context.bot.ban_chat_member(
            chat_id=update.chat_id,
            user_id=target_id,
            until_date=datetime.utcnow()  # Immediate unban = kick
        )
        await context.bot.unban_chat_member(
            chat_id=update.chat_id,
            user_id=target_id
        )
        
        target_name = mention_html(update.message.reply_to_message.from_user) if update.message.reply_to_message else f"User {target_id}"
        await update.message.reply_html(f"🔨 <b>Kicked!</b>\n\n{target_name} has been kicked from the group.")
    except Exception as e:
        await update.message.reply_text(f"❌ Failed to kick user.\nError: {e}")


async def purge_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete messages (purge)"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    if not update.message.reply_to_message:
        await update.message.reply_text("❌ Reply to a message to start purging from there!")
        return
    
    # Get count
    count = 10  # Default
    if context.args:
        try:
            count = min(int(context.args[0]), 100)  # Max 100
        except ValueError:
            pass
    
    # Delete messages from replied message to current
    start_msg_id = update.message.reply_to_message.message_id
    end_msg_id = update.message.message_id
    
    deleted = 0
    for msg_id in range(start_msg_id, min(end_msg_id + 1, start_msg_id + count)):
        try:
            await context.bot.delete_message(chat_id=update.chat_id, message_id=msg_id)
            deleted += 1
        except Exception:
            pass
    
    await update.message.delete()
    msg = await update.message.reply_to_message.reply_text(f"🗑️ Deleted {deleted} messages.")
    
    # Delete confirmation after 3 seconds
    import asyncio
    asyncio.create_task(safe_delete(context.bot, update.chat_id, msg.message_id, 3))


async def safe_delete(bot, chat_id, message_id, delay):
    import asyncio
    await asyncio.sleep(delay)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


async def moderation_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle moderation inline buttons"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data == "mod_close":
        await query.delete_message()


def setup_moderation_handlers(application):
    """Setup moderation handlers"""
    application.add_handler(CommandHandler("ban", ban_command))
    application.add_handler(CommandHandler("mute", mute_command))
    application.add_handler(CommandHandler("warn", warn_command))
    application.add_handler(CommandHandler("kick", kick_command))
    application.add_handler(CommandHandler("purge", purge_command))
    application.add_handler(CallbackQueryHandler(moderation_callback, pattern="^mod_"))
