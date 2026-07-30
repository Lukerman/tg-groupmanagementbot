"""
Configuration loader for the bot.
Handles environment variables and settings validation.
"""

import os
from dataclasses import dataclass, field
from typing import List, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


@dataclass
class Config:
    """Main configuration container."""
    
    # Bot Configuration
    bot_token: str = ""
    admin_ids: List[int] = field(default_factory=list)
    
    # Database
    database_url: str = "sqlite+aiosqlite:///bot.db"
    
    # Logging
    log_level: str = "INFO"
    
    # Performance
    max_connections: int = 100
    cache_ttl: int = 300
    
    # Security
    rate_limit_per_minute: int = 60
    flood_threshold: int = 5
    
    # Feature Flags
    enable_anti_raid: bool = True
    enable_trust_system: bool = True
    enable_activity_tracking: bool = True
    enable_auto_moderation: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        if not self.bot_token:
            raise ValueError("BOT_TOKEN is required")
        
        if self.flood_threshold < 1:
            raise ValueError("FLOOD_THRESHOLD must be at least 1")
        
        if self.rate_limit_per_minute < 1:
            raise ValueError("RATE_LIMIT_PER_MINUTE must be at least 1")


def load_config(env_path: Optional[str] = None) -> Config:
    """
    Load configuration from environment variables.
    
    Args:
        env_path: Path to .env file. If None, looks in standard locations.
    
    Returns:
        Config object with loaded settings.
    """
    # Try to load .env file
    if env_path:
        env_file = Path(env_path)
    else:
        env_file = Path(__file__).parent / ".env"
    
    if env_file.exists():
        logger.info(f"Loading configuration from {env_file}")
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()
    
    # Parse admin IDs
    admin_ids_str = os.getenv("ADMIN_IDS", "")
    admin_ids = []
    if admin_ids_str:
        try:
            admin_ids = [int(x.strip()) for x in admin_ids_str.split(',') if x.strip()]
        except ValueError:
            logger.warning("Invalid ADMIN_IDS format, ignoring")
    
    config = Config(
        bot_token=os.getenv("BOT_TOKEN", ""),
        admin_ids=admin_ids,
        database_url=os.getenv("DATABASE_URL", "sqlite+aiosqlite:///bot.db"),
        log_level=os.getenv("LOG_LEVEL", "INFO"),
        max_connections=int(os.getenv("MAX_CONNECTIONS", "100")),
        cache_ttl=int(os.getenv("CACHE_TTL", "300")),
        rate_limit_per_minute=int(os.getenv("RATE_LIMIT_PER_MINUTE", "60")),
        flood_threshold=int(os.getenv("FLOOD_THRESHOLD", "5")),
        enable_anti_raid=os.getenv("ENABLE_ANTI_RAID", "true").lower() == "true",
        enable_trust_system=os.getenv("ENABLE_TRUST_SYSTEM", "true").lower() == "true",
        enable_activity_tracking=os.getenv("ENABLE_ACTIVITY_TRACKING", "true").lower() == "true",
        enable_auto_moderation=os.getenv("ENABLE_AUTO_MODERATION", "true").lower() == "true",
    )
    
    logger.info("Configuration loaded successfully")
    return config


# Global config instance
config: Optional[Config] = None


def get_config() -> Config:
    """Get the global configuration instance."""
    if config is None:
        raise RuntimeError("Configuration not loaded. Call load_config() first.")
    return config
