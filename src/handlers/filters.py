"""Filters Handler - Auto-responses to keywords"""
from telegram import Update
from telegram.ext import CommandHandler, ContextTypes, CallbackQueryHandler, MessageHandler, filters
from sqlalchemy import select

from src.models.database import ChatSettings, Filter
from src.utils.helpers import check_user_admin, parse_filter_command


async def filter_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Add a new filter"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    user = update.effective_user
    if not await check_user_admin(update.chat_id, user.id, context):
        await update.message.reply_text("❌ Only admins can use this command!")
        return
    
    # Parse trigger and response
    text = update.message.text
    if '|' not in text:
        await update.message.reply_html(
            "⚠️ <b>Usage:</b>\n"
            "<code>/filter trigger | response</code>\n\n"
            "Example:\n"
            "<code>/filter hello | Hi there! Welcome to the group!</code>"
        )
        return
    
    trigger, response = parse_filter_command(text)
    
    if not trigger or not response:
        await update.message.reply_text("❌ Invalid filter format!")
        return
    
    async with context.bot_data['db_session']() as session:
        new_filter = Filter(
            chat_id=update.chat_id,
            trigger=trigger.lower(),
            response=response,
            created_by=user.id
        )
        session.add(new_filter)
        await session.commit()
    
    await update.message.reply_text(f"✅ Filter added!\n\n<b>Trigger:</b> <code>{trigger}</code>\n<b>Response:</b> <code>{response}</code>", parse_mode='HTML')


async def filters_list_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """List all filters"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        await update.message.reply_text("This command only works in groups!")
        return
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Filter).where(Filter.chat_id == update.chat_id)
        )
        all_filters = result.scalars().all()
    
    if not all_filters:
        await update.message.reply_text("📭 No filters set up yet!")
        return
    
    from src.utils.inline_keyboards import get_filters_list_keyboard
    
    text = f"📋 <b>Filters ({len(all_filters)})</b>\n\n"
    for i, f in enumerate(all_filters[:15], 1):
        text += f"{i}. <code>{f.trigger}</code>\n"
    
    if len(all_filters) > 15:
        text += f"\n...and {len(all_filters) - 15} more (use inline buttons)"
    
    await update.message.reply_html(text, reply_markup=get_filters_list_keyboard(all_filters))


async def check_filters(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Check message against filters"""
    if not update.chat_id or update.chat_type not in ["group", "supergroup"]:
        return
    
    message = update.message
    if not message or not message.text:
        return
    
    # Ignore admins
    chat_member = await context.bot.get_chat_member(update.chat_id, message.from_user.id)
    if chat_member.status in ['creator', 'administrator']:
        return
    
    text = message.text.lower()
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Filter).where(Filter.chat_id == update.chat_id)
        )
        all_filters = result.scalars().all()
        
        for f in all_filters:
            if f.trigger.lower() in text:
                await message.reply_text(f.response)
                break


async def filter_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Delete a filter via callback"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("filter_delete_"):
        return
    
    filter_id = int(data.replace("filter_delete_", ""))
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Filter).where(Filter.id == filter_id)
        )
        f = result.scalar_one_or_none()
        
        if f:
            await session.delete(f)
            await session.commit()
            await query.edit_message_text(f"🗑️ Filter '{f.trigger}' deleted!")
        else:
            await query.edit_message_text("❌ Filter not found!")


async def filter_view_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """View filter details"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    if not data.startswith("filter_view_"):
        return
    
    filter_id = int(data.replace("filter_view_", ""))
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(Filter).where(Filter.id == filter_id)
        )
        f = result.scalar_one_or_none()
        
        if f:
            text = (
                f"📄 <b>Filter Details</b>\n\n"
                f"<b>Trigger:</b> <code>{f.trigger}</code>\n"
                f"<b>Response:</b> <code>{f.response}</code>\n"
                f"<b>Type:</b> {f.filter_type}\n"
                f"<b>Created:</b> {f.created_at.strftime('%Y-%m-%d %H:%M')}"
            )
            await query.message.reply_html(text)


async def filter_add_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Prompt to add filter"""
    query = update.callback_query
    await query.answer()
    
    await query.edit_message_text(
        "➕ <b>Add New Filter</b>\n\n"
        "Use the command:\n"
        "<code>/filter trigger | response</code>\n\n"
        "Example:\n"
        "<code>/filter rules | Please read our group rules...</code>",
        parse_mode='HTML'
    )


def setup_filter_handlers(application):
    """Setup filter handlers"""
    application.add_handler(CommandHandler("filter", filter_command))
    application.add_handler(CommandHandler("filters", filters_list_command))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_filters), group=2)
    application.add_handler(CallbackQueryHandler(filter_delete_callback, pattern="^filter_delete_"))
    application.add_handler(CallbackQueryHandler(filter_view_callback, pattern="^filter_view_"))
    application.add_handler(CallbackQueryHandler(filter_add_callback, pattern="^filter_add$"))
