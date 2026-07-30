"""
NexusGuard - Next-Generation Telegram Group Management Bot

A premium moderation bot with innovative features:
- Trust Engine with behavior timelines
- Conversation Rhythm analysis
- Adaptive Cooling Zones
- Community Health tracking
- Member Journey milestones
- And 50+ original modules

© 2024 NexusGuard Bot
"""

import asyncio
import logging
import signal
from typing import List, Optional

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, ChatMemberUpdatedFilter
from aiogram.types import Message, ChatMemberUpdated, CallbackQuery
from aiogram.exceptions import TelegramNetworkError
from aiogram.filters.chat_member_updated import ChatMemberUpdated

from config import load_config, Config
from database import db_manager
from utils.cache import get_cache
from animations.emoji import get_emoji, format_status

# Import routers (will be created)
# from routers import admin, moderation, welcome, stats

logger = logging.getLogger(__name__)


class NexusGuardBot:
    """
    Main bot class orchestrating all components.
    
    Features:
    - Graceful startup/shutdown
    - Error handling and recovery
    - Component lifecycle management
    - Health monitoring
    """
    
    def __init__(self):
        self.config: Optional[Config] = None
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._shutdown_event = asyncio.Event()
    
    async def initialize(self) -> None:
        """Initialize all bot components."""
        logger.info("🛡️ Initializing NexusGuard Bot...")
        
        # Load configuration
        self.config = load_config()
        logger.info(format_status("Configuration loaded", self.config.log_level))
        
        # Initialize database
        await db_manager.initialize()
        logger.info(format_status("Database connected", "✓"))
        
        # Initialize cache
        cache = get_cache()
        logger.info(format_status("Cache initialized", f"max_size={cache._max_size}"))
        
        # Create bot instance
        self.bot = Bot(
            token=self.config.bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )
        
        # Verify bot token
        try:
            bot_info = await self.bot.get_me()
            logger.info(format_status("Bot authenticated", f"@{bot_info.username}"))
        except Exception as e:
            logger.error(f"Failed to authenticate bot: {e}")
            raise
        
        # Create dispatcher
        self.dp = Dispatcher()
        
        # Register routers
        await self._register_routers()
        
        # Register middleware
        await self._register_middleware()
        
        # Register handlers
        await self._register_handlers()
        
        logger.info("✅ NexusGuard Bot initialized successfully")
    
    async def _register_routers(self) -> None:
        """Register all routers with the dispatcher."""
        # These will be implemented in subsequent modules
        # from routers.admin import router as admin_router
        # from routers.moderation import router as moderation_router
        # from routers.welcome import router as welcome_router
        # from routers.stats import router as stats_router
        
        # self.dp.include_router(admin_router)
        # self.dp.include_router(moderation_router)
        # self.dp.include_router(welcome_router)
        # self.dp.include_router(stats_router)
        
        logger.info(format_status("Routers registered", "pending"))
    
    async def _register_middleware(self) -> None:
        """Register middleware components."""
        # from middlewares.auth import AuthMiddleware
        # from middlewares.database import DatabaseMiddleware
        # from middlewares.rate_limit import RateLimitMiddleware
        
        # self.dp.update.middleware(AuthMiddleware())
        # self.dp.update.middleware(DatabaseMiddleware())
        # self.dp.message.middleware(RateLimitMiddleware())
        
        logger.info(format_status("Middleware registered", "pending"))
    
    async def _register_handlers(self) -> None:
        """Register command and message handlers."""
        
        # Start command
        @self.dp.message(Command("start"))
        async def cmd_start(message: Message):
            emoji = get_emoji()
            await message.answer(
                f"{emoji.shield} <b>NexusGuard Bot</b>\n\n"
                f"Welcome to the next generation of group management!\n\n"
                f"{emoji.bullet} Advanced trust system\n"
                f"{emoji.bullet} Conversation rhythm analysis\n"
                f"{emoji.bullet} Adaptive moderation\n"
                f"{emoji.bullet} Community health tracking\n\n"
                f"Use /help to see all commands."
            )
        
        # Help command
        @self.dp.message(Command("help"))
        async def cmd_help(message: Message):
            emoji = get_emoji()
            help_text = (
                f"{emoji.shield} <b>NexusGuard Commands</b>\n\n"
                
                f"{emoji.settings} <b>Admin Commands:</b>\n"
                f"/settings - Group settings\n"
                f"/trust - View trust system\n"
                f"/stats - Group statistics\n"
                f"/moderate - Moderation tools\n\n"
                
                f"{emoji.users} <b>Member Commands:</b>\n"
                f"/mytrust - Your trust score\n"
                f"/badges - Your badges\n"
                f"/activity - Your activity\n\n"
                
                f"{emoji.info} <b>Info:</b>\n"
                f"/ping - Bot status\n"
                f"/rules - Group rules"
            )
            await message.answer(help_text)
        
        # Ping command
        @self.dp.message(Command("ping"))
        async def cmd_ping(message: Message):
            emoji = get_emoji()
            await message.answer(f"{emoji.success} Bot is operational!")
        
        # Member join handler
        @self.dp.chat_member(ChatMemberUpdated.is_member >> F.new_chat_member.is_member)
        async def on_member_join(event: ChatMemberUpdated):
            """Handle new member joins."""
            from services.trust_engine import trust_engine
            
            chat_id = event.chat.id
            user_id = event.from_user.id
            
            async with db_manager.get_session() as session:
                # Award small trust bonus for joining
                await trust_engine.adjust_trust(
                    chat_id=chat_id,
                    user_id=user_id,
                    delta=trust_engine.TRUST_JOIN_BONUS,
                    reason="Member joined the group",
                    session=session,
                    event_type="member_join",
                )
            
            logger.info(f"New member joined: {user_id} in {chat_id}")
        
        # Message handler for rhythm tracking
        @self.dp.message()
        async def on_message(message: Message):
            """Process all messages for rhythm tracking."""
            from services.conversation_rhythm import conversation_rhythm
            from services.trust_engine import trust_engine
            
            if not message.from_user or message.from_user.is_bot:
                return
            
            chat_id = message.chat.id
            user_id = message.from_user.id
            
            async with db_manager.get_session() as session:
                # Check conversation rhythm
                is_allowed, reason = await conversation_rhythm.record_message(
                    chat_id=chat_id,
                    user_id=user_id,
                    session=session,
                )
                
                if not is_allowed:
                    # Delete the message
                    try:
                        await message.delete()
                    except Exception:
                        pass
                    
                    # Notify user (silently)
                    emoji = get_emoji()
                    warning_msg = await message.answer(
                        f"{emoji.warning} Please slow down your messaging.",
                        delete_after=5,
                    )
                    
                    # Penalize trust
                    await trust_engine.penalize_negative_behavior(
                        chat_id=chat_id,
                        user_id=user_id,
                        behavior_type="flood_detected",
                        session=session,
                    )
                    
                    return
                
                # Award small trust for normal messaging
                await trust_engine.award_positive_behavior(
                    chat_id=chat_id,
                    user_id=user_id,
                    behavior_type="active_participation",
                    session=session,
                )
    
    async def start(self) -> None:
        """Start the bot polling."""
        if not self.bot or not self.dp:
            raise RuntimeError("Bot not initialized. Call initialize() first.")
        
        logger.info("🚀 Starting bot polling...")
        
        # Setup signal handlers
        loop = asyncio.get_running_loop()
        for sig in (signal.SIGTERM, signal.SIGINT):
            loop.add_signal_handler(
                sig,
                lambda: asyncio.create_task(self.shutdown()),
            )
        
        # Start polling
        await self.dp.start_polling(
            self.bot,
            allowed_updates=self.dp.resolve_used_update_types(),
        )
    
    async def shutdown(self) -> None:
        """Gracefully shutdown the bot."""
        logger.info("🛑 Shutting down NexusGuard Bot...")
        
        # Stop dispatcher
        if self.dp:
            await self.dp.stop_polling()
        
        # Close bot
        if self.bot:
            try:
                await self.bot.session.close()
            except Exception as e:
                logger.error(f"Error closing bot session: {e}")
        
        # Close database
        await db_manager.close()
        
        logger.info("✅ Shutdown complete")
        self._shutdown_event.set()
    
    async def run(self) -> None:
        """Run the bot until shutdown."""
        try:
            await self.initialize()
            await self.start()
        except Exception as e:
            logger.error(f"Bot error: {e}", exc_info=True)
            raise
        finally:
            await self.shutdown()


async def main():
    """Main entry point."""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    )
    
    # Create and run bot
    bot = NexusGuardBot()
    await bot.run()


if __name__ == "__main__":
    asyncio.run(main())
