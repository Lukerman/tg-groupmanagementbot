"""
Animated Emoji System for premium UX.

Provides a centralized system for using Telegram's animated emojis
throughout the bot interface with consistent styling and theming.
"""

from dataclasses import dataclass
from typing import Optional
from enum import Enum


class EmojiCategory(Enum):
    """Categories of emoji for different contexts."""
    LOADING = "loading"
    SUCCESS = "success"
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"
    CELEBRATION = "celebration"
    MODERATION = "moderation"
    STATS = "stats"
    NAVIGATION = "navigation"
    ACHIEVEMENT = "achievement"
    SEASONAL = "seasonal"


@dataclass
class EmojiSet:
    """A set of related emoji for a specific purpose."""
    
    # Loading states
    loading: str = "⏳"
    loading_dots: str = "…"
    progress: str = "📊"
    
    # Success states
    success: str = "✅"
    check: str = "☑️"
    done: str = "✔️"
    
    # Error states
    error: str = "❌"
    warning: str = "⚠️"
    alert: str = "🚨"
    
    # Info states
    info: str = "ℹ️"
    question: str = "❓"
    bullet: str = "•"
    
    # Celebration
    party: str = "🎉"
    trophy: str = "🏆"
    star: str = "⭐"
    fire: str = "🔥"
    
    # Moderation
    shield: str = "🛡️"
    ban: str = "🚫"
    mute: str = "🔇"
    kick: str = "👢"
    warn: str = "⚡"
    
    # Stats
    chart_up: str = "📈"
    chart_down: str = "📉"
    users: str = "👥"
    messages: str = "💬"
    time: str = "🕐"
    
    # Navigation
    back: str = "◀️"
    forward: str = "▶️"
    up: str = "⬆️"
    down: str = "⬇️"
    home: str = "🏠"
    settings: str = "⚙️"
    
    # Achievements
    medal_bronze: str = "🥉"
    medal_silver: str = "🥈"
    medal_gold: str = "🥇"
    medal_platinum: str = "💎"
    badge: str = "🎖️"
    
    # Seasonal
    winter: str = "❄️"
    spring: str = "🌸"
    summer: str = "☀️"
    autumn: str = "🍂"
    halloween: str = "🎃"
    christmas: str = "🎄"


# Global emoji set instance
_emoji: Optional[EmojiSet] = None


def get_emoji() -> EmojiSet:
    """Get the global emoji set."""
    global _emoji
    if _emoji is None:
        _emoji = EmojiSet()
    return _emoji


def format_status(
    status: str,
    value: any = None,
    icon: Optional[str] = None,
) -> str:
    """
    Format a status line with emoji.
    
    Args:
        status: Status text
        value: Optional value to display
        icon: Optional custom icon
    
    Returns:
        Formatted status string
    """
    emoji = get_emoji()
    
    if icon is None:
        icon = emoji.bullet
    
    if value is not None:
        return f"{icon} <b>{status}:</b> {value}"
    return f"{icon} <b>{status}</b>"


def format_progress(current: int, total: int, width: int = 10) -> str:
    """
    Create a visual progress bar.
    
    Args:
        current: Current value
        total: Total value
        width: Width of the progress bar
    
    Returns:
        Formatted progress bar string
    """
    emoji = get_emoji()
    
    if total == 0:
        percent = 0
    else:
        percent = min(100, max(0, (current / total) * 100))
    
    filled = int(width * percent / 100)
    empty = width - filled
    
    bar = "█" * filled + "░" * empty
    return f"{bar} {percent:.1f}% ({current}/{total})"


def format_badge(tier: str) -> str:
    """
    Get the appropriate badge emoji for a tier.
    
    Args:
        tier: Badge tier (bronze, silver, gold, platinum)
    
    Returns:
        Badge emoji
    """
    emoji = get_emoji()
    
    tier_map = {
        "bronze": emoji.medal_bronze,
        "silver": emoji.medal_silver,
        "gold": emoji.medal_gold,
        "platinum": emoji.medal_platinum,
        "diamond": emoji.medal_platinum,
    }
    
    return tier_map.get(tier.lower(), emoji.badge)


def format_health_score(score: float) -> str:
    """
    Format a health score with appropriate emoji.
    
    Args:
        score: Health score from 0.0 to 1.0
    
    Returns:
        Formatted health indicator
    """
    emoji = get_emoji()
    
    if score >= 0.8:
        icon = emoji.success
        color = "🟢"
    elif score >= 0.6:
        icon = emoji.check
        color = "🟡"
    elif score >= 0.4:
        icon = emoji.warning
        color = "🟠"
    else:
        icon = emoji.error
        color = "🔴"
    
    return f"{color} {icon} {score:.2f}"


def format_trust_level(trust: float) -> str:
    """
    Format a trust level with visual indicators.
    
    Args:
        trust: Trust score from 0.0 to 1.0
    
    Returns:
        Formatted trust indicator
    """
    if trust >= 0.8:
        return f"🟢 High ({trust:.2f})"
    elif trust >= 0.6:
        return f"🟡 Good ({trust:.2f})"
    elif trust >= 0.4:
        return f"🟠 Medium ({trust:.2f})"
    elif trust >= 0.2:
        return f"🔴 Low ({trust:.2f})"
    else:
        return f"⚫ Critical ({trust:.2f})"


__all__ = [
    'EmojiCategory',
    'EmojiSet',
    'get_emoji',
    'format_status',
    'format_progress',
    'format_badge',
    'format_health_score',
    'format_trust_level',
]
