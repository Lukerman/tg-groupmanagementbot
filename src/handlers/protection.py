"""Protection Handlers - Anti-spam, Links, CAPTCHA"""
from telegram import Update
from telegram.ext import MessageHandler, filters, ContextTypes, CallbackQueryHandler
from sqlalchemy import select
from datetime import datetime

from src.models.database import ChatSettings, User, CaptchaSession
from src.utils.helpers import is_link, is_forwarded_message, generate_captcha
from src.utils.inline_keyboards import get_captcha_keyboard


async def check_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Main protection handler for all messages"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        return
    
    message = update.message
    if not message:
        return
    
    # Ignore admins
    chat_member = await context.bot.get_chat_member(update.chat_id, message.from_user.id)
    if chat_member.status in ['creator', 'administrator']:
        return
    
    async with context.bot_data['db_session']() as session:
        # Get chat settings
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == update.chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=update.chat_id)
            session.add(settings)
            await session.commit()
        
        should_delete = False
        reason = ""
        
        # Check links
        if settings.delete_links and message.text and is_link(message.text):
            should_delete = True
            reason = "Links are not allowed"
        
        # Check forwarded messages
        if settings.delete_forwarded and is_forwarded_message(message):
            should_delete = True
            reason = "Forwarded messages are not allowed"
        
        # Check anti-spam (basic implementation)
        if settings.anti_spam and message.text:
            hashtag_count = len([e for e in (message.entities or []) if e.type == 'hashtag'])
            mention_count = len([e for e in (message.entities or []) if e.type == 'mention'])
            
            if hashtag_count > 5:
                should_delete = True
                reason = "Too many hashtags"
            elif mention_count > 10:
                should_delete = True
                reason = "Too many mentions"
        
        # Delete message if needed
        if should_delete:
            try:
                await message.delete()
                await message.reply_text(
                    f"⚠️ {message.from_user.mention_html()} - {reason}",
                    parse_mode='HTML'
                )
            except Exception:
                pass
        
        await session.commit()


async def handle_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the group"""
    if not update.chat_id:
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
        
        # Handle CAPTCHA
        if settings.captcha_enabled:
            for user in update.message.new_chat_members:
                if user.is_bot:
                    continue
                
                # Generate CAPTCHA
                question, answer = generate_captcha()
                
                captcha_msg = await update.message.reply_text(
                    f"🤖 <b>CAPTCHA for {user.mention_html()}</b>\n\n"
                    f"Solve this to verify: <b>{question}</b>\n\n"
                    f"You have 60 seconds.",
                    parse_mode='HTML',
                    reply_markup=get_captcha_keyboard(answer, settings.theme)
                )
                
                # Save CAPTCHA session
                captcha_session = CaptchaSession(
                    chat_id=update.chat_id,
                    user_id=user.id,
                    message_id=captcha_msg.message_id,
                    answer=answer,
                    expires_at=datetime.utcnow()
                )
                session.add(captcha_session)
                await session.commit()
                
                # Restrict user until CAPTCHA solved
                try:
                    await context.bot.restrict_chat_member(
                        chat_id=update.chat_id,
                        user_id=user.id,
                        can_send_messages=False,
                        can_send_media_messages=False,
                        can_send_other_messages=False,
                        can_add_web_page_previews=False,
                    )
                except Exception:
                    pass
        
        # Send welcome message
        elif settings.welcome_enabled:
            for user in update.message.new_chat_members:
                welcome_text = settings.welcome_message.format(
                    mention=user.mention_html(),
                    title=update.effective_chat.title,
                    username=f"@{user.username}" if user.username else "N/A",
                    first_name=user.first_name
                )
                
                try:
                    await update.message.reply_html(welcome_text)
                except Exception:
                    await update.message.reply_text(
                        f"Welcome {user.first_name} to {update.effective_chat.title}! 🎉"
                    )
        
        await session.commit()


async def captcha_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle CAPTCHA button clicks"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("captcha_"):
        return
    
    answer = data.replace("captcha_", "")
    user_id = query.from_user.id
    chat_id = query.message.chat_id
    
    async with context.bot_data['db_session']() as session:
        # Find CAPTCHA session
        result = await session.execute(
            select(CaptchaSession).where(
                CaptchaSession.chat_id == chat_id,
                CaptchaSession.user_id == user_id,
                CaptchaSession.solved == False
            )
        )
        captcha = result.scalar_one_or_none()
        
        if not captcha:
            await query.edit_message_text("❌ CAPTCHA session expired or already solved!")
            return
        
        if captcha.answer == answer:
            # Correct answer
            captcha.solved = True
            await session.commit()
            
            # Unrestrict user
            try:
                await context.bot.restrict_chat_member(
                    chat_id=chat_id,
                    user_id=user_id,
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True,
                )
            except Exception:
                pass
            
            await query.edit_message_text(f"✅ Verification successful! Welcome to the group!")
            
            # Delete CAPTCHA message after 5 seconds
            import asyncio
            asyncio.create_task(safe_delete_message(context.bot, chat_id, query.message.message_id))
        else:
            # Wrong answer
            await query.answer("❌ Wrong answer! Try again.", show_alert=True)


async def safe_delete_message(bot, chat_id, message_id):
    """Safely delete a message"""
    import asyncio
    await asyncio.sleep(5)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:
        pass


def setup_protection_handlers(application):
    """Setup protection handlers"""
    # Message protection
    application.add_handler(MessageHandler(
        filters.ALL & ~filters.STATUS_UPDATE,
        check_protection
    ), group=1)
    
    # New member handler
    application.add_handler(MessageHandler(
        filters.StatusUpdate.NEW_CHAT_MEMBERS,
        handle_new_member
    ))
    
    # CAPTCHA callback
    application.add_handler(CallbackQueryHandler(captcha_callback, pattern="^captcha_"))
