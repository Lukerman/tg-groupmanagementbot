from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from src.models.database import get_session, GroupSettings, UserWarnings, CaptchaChallenge
from src.utils.helpers import format_welcome_message, is_admin
from src.utils.inline_keyboards import build_captcha_keyboard
import random

async def on_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle new members joining the group"""
    if not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        return
    
    chat = update.effective_chat
    db = get_session()
    
    try:
        settings = db.query(GroupSettings).filter_by(chat_id=chat.id).first()
        
        for user in update.effective_message.new_chat_members:
            # Skip bots
            if user.is_bot:
                continue
            
            # Check if CAPTCHA is enabled
            if settings and settings.captcha_enabled:
                # Generate simple math CAPTCHA
                num1 = random.randint(1, 10)
                num2 = random.randint(1, 10)
                answer = num1 + num2
                
                # Store challenge
                captcha = CaptchaChallenge(
                    chat_id=chat.id,
                    user_id=user.id,
                    answer=answer,
                    message_id=0
                )
                db.add(captcha)
                db.commit()
                
                # Send CAPTCHA message
                captcha_msg = await context.bot.send_message(
                    chat_id=chat.id,
                    text=f"🤖 {user.mention_html()}, please solve: {num1} + {num2} = ?",
                    reply_markup=build_captcha_keyboard(answer)
                )
                
                # Update message_id
                captcha.message_id = captcha_msg.message_id
                db.commit()
                
            elif settings and settings.welcome_enabled:
                # Send welcome message
                welcome_text = format_welcome_message(
                    settings.welcome_message,
                    user,
                    chat.title
                )
                await context.bot.send_message(
                    chat_id=chat.id,
                    text=welcome_text,
                    parse_mode="HTML"
                )
                
    finally:
        db.close()

async def on_member_left(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle members leaving the group"""
    if not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        return
    
    chat = update.effective_chat
    user = update.effective_message.left_chat_member
    db = get_session()
    
    try:
        settings = db.query(GroupSettings).filter_by(chat_id=chat.id).first()
        
        if settings and settings.goodbye_enabled:
            goodbye_text = format_welcome_message(
                settings.goodbye_message,
                user,
                chat.title
            )
            await context.bot.send_message(
                chat_id=chat.id,
                text=goodbye_text,
                parse_mode="HTML"
            )
            
    finally:
        db.close()

async def verify_captcha(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Verify CAPTCHA answer from callback"""
    query = update.callback_query
    await query.answer()
    
    if not query.data.startswith("captcha_"):
        return
    
    answer = int(query.data.split("_")[1])
    db = get_session()
    
    try:
        # Find challenge (simplified - in production use proper lookup)
        challenge = db.query(CaptchaChallenge).filter_by(
            user_id=query.from_user.id,
            answer=answer
        ).first()
        
        if challenge:
            # Correct answer
            await query.edit_message_text(f"✅ Verified! Welcome to the group.")
            
            # Give user permissions back
            await context.bot.restrict_chat_member(
                chat_id=challenge.chat_id,
                user_id=query.from_user.id,
                permissions=ChatPermissions(
                    can_send_messages=True,
                    can_send_media_messages=True,
                    can_send_other_messages=True,
                    can_add_web_page_previews=True
                )
            )
            
            # Delete challenge
            db.delete(challenge)
            db.commit()
            
            # Try to delete CAPTCHA message
            try:
                await context.bot.delete_message(
                    chat_id=challenge.chat_id,
                    message_id=challenge.message_id
                )
            except:
                pass
        else:
            await query.answer("❌ Wrong answer!", show_alert=True)
            
    finally:
        db.close()
