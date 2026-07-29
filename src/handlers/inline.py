"""Inline Query Handlers and Callback Dispatcher"""
from telegram import Update
from telegram.ext import CallbackQueryHandler, ContextTypes, InlineQueryHandler
from sqlalchemy import select

from src.models.database import ChatSettings, Note, Filter
from src.utils.inline_keyboards import (
    get_main_menu_keyboard,
    get_protection_settings_keyboard,
    get_theme_selection_keyboard,
    get_permissions_keyboard,
    ThemeManager
)
from src.utils.helpers import check_user_admin


async def settings_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle all settings-related callback queries"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    chat_id = query.message.chat_id
    
    # Only work in groups
    if not chat_id or str(chat_id).startswith('-'):
        pass  # Continue processing
    else:
        return
    
    async with context.bot_data['db_session']() as session:
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == abs(chat_id))
        )
        settings = result.scalar_one_or_none()
        
        if not settings:
            settings = ChatSettings(chat_id=abs(chat_id))
            session.add(settings)
            await session.commit()
        
        theme = settings.theme or "default"
        
        # Protection settings
        if data == "settings_protection":
            await query.edit_message_text(
                "🛡️ <b>Protection Settings</b>\n\n"
                "Configure group protection options:",
                parse_mode='HTML',
                reply_markup=get_protection_settings_keyboard(theme)
            )
        
        # Welcome settings
        elif data == "settings_welcome":
            from src.utils.inline_keyboards import get_welcome_settings_keyboard
            await query.edit_message_text(
                "👋 <b>Welcome Settings</b>\n\n"
                "Configure welcome and goodbye messages:",
                parse_mode='HTML',
                reply_markup=get_welcome_settings_keyboard(theme)
            )
        
        # Filters
        elif data == "settings_filters":
            result = await session.execute(
                select(Filter).where(Filter.chat_id == abs(chat_id))
            )
            all_filters = result.scalars().all()
            
            from src.utils.inline_keyboards import get_filters_list_keyboard
            text = f"⚠️ <b>Filters ({len(all_filters)})</b>\n\nManage auto-responses:"
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=get_filters_list_keyboard(all_filters, theme)
            )
        
        # Notes
        elif data == "settings_notes":
            result = await session.execute(
                select(Note).where(Note.chat_id == abs(chat_id))
            )
            all_notes = result.scalars().all()
            
            from src.utils.inline_keyboards import get_notes_list_keyboard
            text = f"📝 <b>Notes ({len(all_notes)})</b>\n\nManage saved notes:"
            await query.edit_message_text(
                text,
                parse_mode='HTML',
                reply_markup=get_notes_list_keyboard(all_notes, theme)
            )
        
        # Theme selection
        elif data == "settings_theme":
            await query.edit_message_text(
                f"🎨 <b>Current Theme:</b> {theme.capitalize()}\n\n"
                "Select a new theme for your group:",
                parse_mode='HTML',
                reply_markup=get_theme_selection_keyboard(theme)
            )
        
        # Permissions
        elif data == "settings_permissions":
            await query.edit_message_text(
                "🔧 <b>Chat Permissions</b>\n\n"
                "Configure what members can do:",
                parse_mode='HTML',
                reply_markup=get_permissions_keyboard(settings, theme)
            )
        
        # Statistics
        elif data == "settings_stats":
            # Count members, messages, etc.
            try:
                chat = await context.bot.get_chat(abs(chat_id))
                member_count = await chat.get_member_count()
                
                stats_text = (
                    f"📊 <b>Group Statistics</b>\n\n"
                    f"👥 <b>Members:</b> {member_count}\n"
                    f"📝 <b>Title:</b> {chat.title}\n"
                    f"🆔 <b>ID:</b> <code>{chat.id}</code>\n"
                    f"📌 <b>Type:</b> {chat.type}\n\n"
                    f"<i>More stats coming soon!</i>"
                )
                await query.edit_message_text(
                    stats_text,
                    parse_mode='HTML',
                    reply_markup=get_main_menu_keyboard(theme)
                )
            except Exception as e:
                await query.edit_message_text(f"❌ Error fetching stats: {e}")
        
        # Help
        elif data == "settings_help":
            help_text = (
                "❓ <b>Help & Support</b>\n\n"
                "<b>Quick Start:</b>\n"
                "1. Add me to your group\n"
                "2. Make me an admin\n"
                "3. Use /settings to configure\n\n"
                "<b>Features:</b>\n"
                "• Auto-moderation\n"
                "• Welcome messages\n"
                "• Filters & Notes\n"
                "• CAPTCHA verification\n"
                "• Custom themes\n\n"
                f"Support: {context.bot_data.get('support_chat', '@telegram')}"
            )
            await query.edit_message_text(
                help_text,
                parse_mode='HTML',
                reply_markup=get_main_menu_keyboard(theme)
            )
        
        # Back to main
        elif data == "settings_back_main":
            await query.edit_message_text(
                "⚙️ <b>Group Settings</b>\n\n"
                "Select an option to configure:",
                parse_mode='HTML',
                reply_markup=get_main_menu_keyboard(theme)
            )
        
        # Theme setting
        elif data.startswith("theme_set_"):
            new_theme = data.replace("theme_set_", "")
            settings.theme = new_theme
            await session.commit()
            
            await query.edit_message_text(
                f"✅ Theme changed to <b>{new_theme.capitalize()}</b>!",
                parse_mode='HTML',
                reply_markup=get_theme_selection_keyboard(new_theme)
            )
        
        # Protection toggles
        elif data.startswith("protect_"):
            setting_map = {
                "protect_links_toggle": "delete_links",
                "protect_forward_toggle": "delete_forwarded",
                "protect_bot_toggle": "captcha_enabled",
                "protect_channel_toggle": "protect_channels",
                "protect_captcha_toggle": "captcha_enabled",
                "protect_spam_toggle": "anti_spam",
            }
            
            if data in setting_map:
                attr = setting_map[data]
                setattr(settings, attr, not getattr(settings, attr))
                await session.commit()
                
                status = "✅ ON" if getattr(settings, attr) else "❌ OFF"
                await query.edit_message_text(
                    f"🛡️ Protection Updated\n\n"
                    f"{attr.replace('_', ' ').title()}: {status}",
                    reply_markup=get_protection_settings_keyboard(theme)
                )


async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle inline queries"""
    query = update.inline_query
    
    if not query.query:
        return
    
    results = []
    
    # Search notes
    if query.query.startswith("note "):
        note_name = query.query.replace("note ", "").lower().strip()
        
        async with context.bot_data['db_session']() as session:
            result = await session.execute(
                select(Note).where(Note.name.like(f"%{note_name}%"))
            )
            notes = result.scalars().all()[:10]
            
            from telegram import InlineQueryResultArticle, InputTextMessageContent
            
            for note in notes:
                results.append(
                    InlineQueryResultArticle(
                        id=f"note_{note.id}",
                        title=f"📝 {note.name}",
                        description=note.content[:50] + "..." if len(note.content) > 50 else note.content,
                        input_message_content=InputTextMessageContent(
                            message_text=note.content
                        )
                    )
                )
    
    await update.inline_query.answer(results, cache_time=300, is_personal=True)


def setup_inline_handlers(application):
    """Setup inline handlers"""
    # Callback query handler for all settings
    application.add_handler(CallbackQueryHandler(
        settings_callback,
        pattern="^settings_|^theme_set_|^protect_"
    ))
    
    # Inline query handler
    application.add_handler(InlineQueryHandler(inline_query))
