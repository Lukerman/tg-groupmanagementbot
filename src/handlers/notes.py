"""Notes Handler - Save and share information"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler
from sqlalchemy import select

from src.models.database import ChatSettings, Note
from src.utils.helpers import check_user_admin, parse_note_command


async def addnote_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new note"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    # Parse name and content
    text = update.message.text
    if '|' not in text:
        await update.message.reply_html(
            "⚠️ <b>Usage:</b>\n"
            "<code>/addnote name | content</code>\n\n"
            "Example:\n"
            "<code>/addnote rules | 1. Be respectful\\n2. No spam\\n3. Have fun!</code>"
        )
        return
    
    name, content = parse_note_command(text)
    
    if not name or not content:
        await update.message.reply_text("❌ Invalid note format!")
        return
    
    async with context.bot_data['db_session']() as session:
        new_note = Note(
            chat_id=update.chat_id,
            name=name.lower(),
            content=content,
            created_by=user.id
        )
        session.add(new_note)
        await session.commit()
    
    await update.message.reply_text(f"✅ Note '{name}' saved!", parse_mode='HTML')


async def notes_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all notes"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Note).where(Note.chat_id == update.chat_id)
        )
        all_notes = result.scalars().all()
    
    if not all_notes:
        await update.message.reply_text("📭 No notes saved yet!")
        return
    
    from src.utils.inline_keyboards import get_notes_list_keyboard
    
    text = f"📋 <b>Notes ({len(all_notes)})</b>\n\n"
    for i, note in enumerate(all_notes[:15], 1):
        text += f"{i}. <code>{note.name}</code>\n"
    
    if len(all_notes) > 15:
        text += f"\n...and {len(all_notes) - 15} more (use inline buttons)"
    
    await update.message.reply_html(text, reply_markup=get_notes_list_keyboard(all_notes))


async def get_note_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Get a specific note"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        return
    
    if not context.args:
        return
    
    note_name = context.args[0].lower()
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Note).where(
                Note.chat_id == update.chat_id,
                Note.name == note_name
            )
        )
        note = result.scalar_one_or_none()
        
        if note:
            await update.message.reply_text(note.content)
        else:
            # Check if user typed /notename without /get
            alt_result = await session.execute(
                select(Note).where(
                    Note.chat_id == update.chat_id,
                    Note.name == update.message.text.replace('/', '').lower()
                )
            )
            alt_note = alt_result.scalar_one_or_none()
            if alt_note:
                await update.message.reply_text(alt_note.content)


async def note_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a note via callback"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("note_delete_"):
        return
    
    note_id = int(data.replace("note_delete_", ""))
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Note).where(Note.id == note_id)
        )
        note = result.scalar_one_or_none()
        
        if note:
            note_name = note.name
            await session.delete(note)
            await session.commit()
            await query.edit_message_text(f"🗑️ Note '{note_name}' deleted!")
        else:
            await query.edit_message_text("❌ Note not found!")


async def note_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View note details"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("note_view_"):
        return
    
    note_id = int(data.replace("note_view_", ""))
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Note).where(Note.id == note_id)
        )
        note = result.scalar_one_or_none()
        
        if note:
            text = (
                f"📝 <b>Note: {note.name.capitalize()}</b>\n\n"
                f"{note.content}\n\n"
                f"<i>Created: {note.created_at.strftime('%Y-%m-%d %H:%M')}</i>"
            )
            await query.message.reply_text(text)


async def note_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt to add note"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ <b>Add New Note</b>\n\n"
        "Use the command:\n"
        "<code>/addnote name | content</code>\n\n"
        "Example:\n"
        "<code>/addnote info | Welcome to our group! Here's some info...</code>",
        parse_mode='HTML'
    )


def setup_note_handlers(application):
    """Setup note handlers"""
    application.add_handler(CommandHandler("addnote", addnote_command))
    application.add_handler(CommandHandler("notes", notes_list_command))
    application.add_handler(CommandHandler("get", get_note_command))
    
    # Also handle direct note names like /rules
    application.add_handler(CommandHandler("note", get_note_command))
    
    application.add_handler(CallbackQueryHandler(note_delete_callback, pattern="^note_delete_"))
    application.add_handler(CallbackQueryHandler(note_view_callback, pattern="^note_view_"))
    application.add_handler(CallbackQueryHandler(note_add_callback, pattern="^note_add$"))
