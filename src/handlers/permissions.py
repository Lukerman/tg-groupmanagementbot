from telegram import Update, ChatMemberAdministrator, ChatMemberOwner
from telegram.ext import ContextTypes
from sqlalchemy.orm import Session
import sys
sys.path.append('..')
from src.db_operations import get_group, create_or_update_user, is_banned, is_muted
from src.utils.helpers import mention_user

async def check_admin(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session) -> bool:
    """Check if the user is an admin in the group"""
    user = update.effective_user
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        return False
    
    try:
        member = await chat.get_member(user.id)
        return isinstance(member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception:
        return False

async def check_creator(update: Update, context: ContextTypes.DEFAULT_TYPE, db: Session) -> bool:
    """Check if the user is the creator of the group"""
    user = update.effective_user
    chat = update.effective_chat
    
    if not chat or chat.type == 'private':
        return False
    
    try:
        member = await chat.get_member(user.id)
        return isinstance(member, ChatMemberOwner) and member.is_anonymous == False
    except Exception:
        return False

async def check_bot_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    """Check if the bot is an admin in the group"""
    chat = update.effective_chat
    if not chat or chat.type == 'private':
        return False
    
    try:
        bot_member = await chat.get_member(context.bot.id)
        return isinstance(bot_member, (ChatMemberAdministrator, ChatMemberOwner))
    except Exception:
        return False

async def is_sudo_user(user_id: int) -> bool:
    """Check if user is a sudo/admin user (bot owner)"""
    # This should be configured from environment variables
    sudo_users = [123456789]  # Replace with actual admin IDs
    return user_id in sudo_users

async def check_permissions(update: Update, context: ContextTypes.DEFAULT_TYPE, 
                           can_delete: bool = False, can_restrict: bool = False) -> bool:
    """Check specific bot permissions"""
    chat = update.effective_chat
    if not chat or chat.type == 'private':
        return False
    
    try:
        bot_member = await chat.get_member(context.bot.id)
        if isinstance(bot_member, ChatMemberOwner):
            return True
        elif isinstance(bot_member, ChatMemberAdministrator):
            if can_delete and not bot_member.can_delete_messages:
                return False
            if can_restrict and not bot_member.can_restrict_members:
                return False
            return True
        return False
    except Exception:
        return False
