from telegram import Update
from telegram.ext import ContextTypes
from src.models.database import get_session, Filter as FilterModel

async def add_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new filter"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    
    # Check args: /filter keyword | response
    if not context.args or len(context.args) < 2:
        await update.effective_message.reply_text(
            "📝 Usage: /filter keyword | response\nExample: /filter hello | Hi there!"
        )
        return
    
    # Parse keyword and response
    full_text = " ".join(context.args)
    if "|" not in full_text:
        await update.effective_message.reply_text("❌ Use | to separate keyword and response")
        return
    
    parts = full_text.split("|", 1)
    keyword = parts[0].strip().lower()
    response = parts[1].strip()
    
    db = get_session()
    try:
        # Check if filter exists
        existing = db.query(FilterModel).filter_by(
            chat_id=chat.id,
            keyword=keyword
        ).first()
        
        if existing:
            existing.response = response
            await update.effective_message.reply_text(f"✅ Filter '{keyword}' updated.")
        else:
            new_filter = FilterModel(
                chat_id=chat.id,
                keyword=keyword,
                response=response
            )
            db.add(new_filter)
            await update.effective_message.reply_text(f"✅ Filter '{keyword}' added.")
        
        db.commit()
    finally:
        db.close()

async def list_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all filters in the group"""
    if not update.effective_chat:
        return
    
    chat = update.effective_chat
    db = get_session()
    
    try:
        filters = db.query(FilterModel).filter_by(chat_id=chat.id).all()
        
        if not filters:
            await update.effective_message.reply_text("📭 No filters set.")
            return
        
        filter_list = "\n".join([f"• {f.keyword}" for f in filters])
        await update.effective_message.reply_text(f"📋 Filters in this group:\n{filter_list}")
    finally:
        db.close()

async def remove_filter(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a filter"""
    if not update.effective_chat or not context.args:
        await update.effective_message.reply_text("📝 Usage: /removefilter keyword")
        return
    
    chat = update.effective_chat
    keyword = context.args[0].lower()
    
    db = get_session()
    try:
        filter_obj = db.query(FilterModel).filter_by(
            chat_id=chat.id,
            keyword=keyword
        ).first()
        
        if filter_obj:
            db.delete(filter_obj)
            db.commit()
            await update.effective_message.reply_text(f"✅ Filter '{keyword}' removed.")
        else:
            await update.effective_message.reply_text(f"❌ Filter '{keyword}' not found.")
    finally:
        db.close()

async def check_filter_response(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check message against filters and respond"""
    if not update.effective_chat or not update.effective_message or not update.effective_message.text:
        return
    
    chat = update.effective_chat
    text = update.effective_message.text.lower()
    
    db = get_session()
    try:
        filters = db.query(FilterModel).filter_by(chat_id=chat.id).all()
        
        for f in filters:
            if f.keyword in text:
                await update.effective_message.reply_text(f.response)
                break
    finally:
        db.close()
