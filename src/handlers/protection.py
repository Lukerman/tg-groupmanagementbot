from telegram import Update, ChatPermissions
from telegram.ext import ContextTypes
from src.models.database import get_session, GroupSettings, UserWarnings
from src.utils.helpers import is_admin

async def check_protection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check if message should be deleted based on protection settings"""
    if not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        return
    
    chat_id = update.effective_chat.id
    db = get_session()
    
    try:
        settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
        
        if not settings or not settings.protection_enabled:
            return
        
        # Check for links
        if settings.delete_links and update.effective_message:
            text = update.effective_message.text or ""
            if "http://" in text or "https://" in text or "t.me/" in text:
                await update.effective_message.delete()
                return
        
        # Check for forwarded messages
        if settings.delete_forwards and update.effective_message and update.effective_message.forward_from:
            await update.effective_message.delete()
            
    finally:
        db.close()

async def anti_spam_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Basic anti-spam detection"""
    if not update.effective_chat or update.effective_chat.type not in ["group", "supergroup"]:
        return
    
    chat_id = update.effective_chat.id
    user_id = update.effective_user.id
    
    # Skip admins
    admins = await update.effective_chat.get_administrators()
    if is_admin(user_id, admins):
        return
    
    db = get_session()
    
    try:
        settings = db.query(GroupSettings).filter_by(chat_id=chat_id).first()
        
        if not settings or not settings.anti_spam:
            return
        
        # Track message frequency (simplified)
        if not hasattr(context.chat_data, 'msg_count'):
            context.chat_data['msg_count'] = {}
        
        if user_id not in context.chat_data['msg_count']:
            context.chat_data['msg_count'][user_id] = 0
        
        context.chat_data['msg_count'][user_id] += 1
        
        # If user sends more than 5 messages in short time, warn
        if context.chat_data['msg_count'][user_id] > 5:
            await update.effective_message.delete()
            
    finally:
        db.close()
