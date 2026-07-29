from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from src.models.database import get_session, Note as NoteModel

async def add_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new note"""
    if not update.effective_chat or not update.effective_user:
        return
    
    chat = update.effective_chat
    
    # Check args: /note name | content
    if not context.args or len(context.args) < 2:
        await update.effective_message.reply_text(
            "📝 Usage: /note name | content\nExample: /note rules | 1. Be nice..."
        )
        return
    
    # Parse name and content
    full_text = " ".join(context.args)
    if "|" not in full_text:
        await update.effective_message.reply_text("❌ Use | to separate name and content")
        return
    
    parts = full_text.split("|", 1)
    name = parts[0].strip().lower()
    content = parts[1].strip()
    
    db = get_session()
    try:
        existing = db.query(NoteModel).filter_by(
            chat_id=chat.id,
            name=name
        ).first()
        
        if existing:
            existing.content = content
            await update.effective_message.reply_text(f"✅ Note '{name}' updated.")
        else:
            new_note = NoteModel(
                chat_id=chat.id,
                name=name,
                content=content
            )
            db.add(new_note)
            await update.effective_message.reply_text(f"✅ Note '{name}' added.")
        
        db.commit()
    finally:
        db.close()

async def list_notes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all notes in the group"""
    if not update.effective_chat:
        return
    
    chat = update.effective_chat
    db = get_session()
    
    try:
        notes = db.query(NoteModel).filter_by(chat_id=chat.id).all()
        
        if not notes:
            await update.effective_message.reply_text("📭 No notes set.")
            return
        
        keyboard = []
        for note in notes:
            keyboard.append([InlineKeyboardButton(
                f"📒 {note.name}",
                callback_data=f"note_view_{chat.id}_{note.name}"
            )])
        
        await update.effective_message.reply_text(
            "📋 Notes in this group:",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
    finally:
        db.close()

async def view_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View a specific note"""
    if not update.effective_chat or not context.args:
        return
    
    chat = update.effective_chat
    name = context.args[0].lower()
    
    db = get_session()
    try:
        note = db.query(NoteModel).filter_by(
            chat_id=chat.id,
            name=name
        ).first()
        
        if note:
            await update.effective_message.reply_text(f"📒 **{name}**\n\n{note.content}")
        else:
            await update.effective_message.reply_text(f"❌ Note '{name}' not found.")
    finally:
        db.close()

async def remove_note(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Remove a note"""
    if not update.effective_chat or not context.args:
        await update.effective_message.reply_text("📝 Usage: /removenote name")
        return
    
    chat = update.effective_chat
    name = context.args[0].lower()
    
    db = get_session()
    try:
        note = db.query(NoteModel).filter_by(
            chat_id=chat.id,
            name=name
        ).first()
        
        if note:
            db.delete(note)
            db.commit()
            await update.effective_message.reply_text(f"✅ Note '{name}' removed.")
        else:
            await update.effective_message.reply_text(f"❌ Note '{name}' not found.")
    finally:
        db.close()

async def inline_note_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline query for notes"""
    if not update.inline_query:
        return
    
    query = update.inline_query.query.strip().lower()
    
    if not query:
        return
    
    db = get_session()
    try:
        # Search notes across all chats (simplified - in production filter by chat)
        notes = db.query(NoteModel).filter(NoteModel.name.contains(query)).limit(10).all()
        
        results = []
        for note in notes:
            results.append({
                'type': 'article',
                'id': f"{note.chat_id}_{note.name}",
                'title': note.name,
                'input_message_content': {'message_text': f"📒 **{note.name}**\n\n{note.content}"},
                'description': note.content[:50] + "..." if len(note.content) > 50 else note.content
            })
        
        await update.inline_query.answer(results)
    finally:
        db.close()
