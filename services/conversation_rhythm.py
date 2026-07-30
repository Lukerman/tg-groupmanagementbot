"""
Conversation Rhythm Service - Advanced Anti-Flood System.

Instead of simple message counting, this system analyzes the rhythm
and patterns of user messaging to detect abnormal behavior while
allowing natural conversation flow.

Features:
- Rhythm pattern analysis
- Burst detection with context awareness
- Adaptive thresholds based on chat activity
- Conversation flow scoring
- Natural language burst tolerance
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from collections import deque
import logging
import math

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models import ChatMember, ChatSettings, TimelineEvent, AdaptivePermission
from utils.cache import get_cache

logger = logging.getLogger(__name__)


@dataclass
class MessagePattern:
    """Represents a user's messaging pattern."""
    
    # Timing
    timestamps: deque = field(default_factory=lambda: deque(maxlen=100))
    
    # Metrics
    avg_interval: float = 0.0  # Average time between messages
    std_deviation: float = 0.0  # Variance in timing
    burst_count: int = 0  # Current burst counter
    
    # Rhythm score (1.0 = perfect rhythm, lower = more erratic)
    rhythm_score: float = 1.0
    
    # Last update
    last_updated: datetime = field(default_factory=datetime.utcnow)


@dataclass
class ChatActivityState:
    """Tracks overall chat activity for adaptive thresholds."""
    
    # Activity metrics
    messages_per_minute: float = 0.0
    active_users: int = 0
    peak_activity: float = 0.0
    
    # Time-based patterns
    hour_of_day: int = 0
    day_of_week: int = 0
    
    # Thresholds
    base_flood_threshold: int = 5
    adaptive_threshold: float = 1.0


class ConversationRhythm:
    """
    Analyzes and manages conversation rhythm for flood detection.
    
    This is NOT a simple flood detector. It understands:
    - Natural conversation bursts (excitement, discussions)
    - Abnormal spam patterns (bot-like behavior)
    - Context-aware thresholds (busy vs quiet periods)
    - Individual user baselines
    """
    
    # Configuration
    DEFAULT_WINDOW_SECONDS = 60
    DEFAULT_BURST_THRESHOLD = 5
    MIN_RHYTHM_SCORE = 0.1
    MAX_RHYTHM_SCORE = 1.0
    
    # Pattern weights
    TIMING_WEIGHT = 0.4
    BURST_WEIGHT = 0.3
    CONSISTENCY_WEIGHT = 0.3
    
    def __init__(self):
        self._user_patterns: Dict[int, Dict[int, MessagePattern]] = {}  # chat_id -> user_id -> pattern
        self._chat_states: Dict[int, ChatActivityState] = {}
        self._cache = get_cache()
        self._lock = asyncio.Lock()
    
    async def record_message(
        self,
        chat_id: int,
        user_id: int,
        session: AsyncSession,
    ) -> Tuple[bool, str]:
        """
        Record a message and analyze rhythm.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            session: Database session
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        async with self._lock:
            now = datetime.utcnow()
            
            # Get or create pattern for this user
            pattern = self._get_or_create_pattern(chat_id, user_id)
            
            # Add timestamp
            pattern.timestamps.append(now)
            
            # Calculate metrics
            await self._update_pattern_metrics(pattern)
            
            # Check for violations
            is_allowed, reason = await self._check_rhythm_violation(
                chat_id, user_id, pattern, session
            )
            
            # Update database
            await self._sync_to_database(chat_id, user_id, pattern, session)
            
            pattern.last_updated = now
            
            if not is_allowed:
                logger.info(
                    f"Rhythm violation for {user_id} in {chat_id}: {reason}"
                )
            
            return is_allowed, reason
    
    def _get_or_create_pattern(
        self,
        chat_id: int,
        user_id: int,
    ) -> MessagePattern:
        """Get or create a message pattern for a user."""
        if chat_id not in self._user_patterns:
            self._user_patterns[chat_id] = {}
        
        if user_id not in self._user_patterns[chat_id]:
            self._user_patterns[chat_id][user_id] = MessagePattern()
        
        return self._user_patterns[chat_id][user_id]
    
    async def _update_pattern_metrics(self, pattern: MessagePattern) -> None:
        """Update pattern metrics based on recent timestamps."""
        if len(pattern.timestamps) < 2:
            return
        
        # Calculate intervals
        timestamps = list(pattern.timestamps)
        intervals = [
            (timestamps[i] - timestamps[i-1]).total_seconds()
            for i in range(1, len(timestamps))
        ]
        
        if not intervals:
            return
        
        # Calculate average interval
        pattern.avg_interval = sum(intervals) / len(intervals)
        
        # Calculate standard deviation
        if len(intervals) > 1:
            variance = sum((x - pattern.avg_interval) ** 2 for x in intervals) / len(intervals)
            pattern.std_deviation = math.sqrt(variance)
        else:
            pattern.std_deviation = 0.0
        
        # Calculate rhythm score
        pattern.rhythm_score = await self._calculate_rhythm_score(pattern)
    
    async def _calculate_rhythm_score(self, pattern: MessagePattern) -> float:
        """
        Calculate a rhythm score based on messaging patterns.
        
        Higher score = more natural, human-like rhythm
        Lower score = more erratic, bot-like behavior
        """
        if pattern.avg_interval == 0:
            return self.MIN_RHYTHM_SCORE
        
        # Factor 1: Timing consistency (humans are inconsistent)
        # Very low std dev can indicate bot behavior
        cv = pattern.std_deviation / pattern.avg_interval if pattern.avg_interval > 0 else 0
        timing_score = min(1.0, max(0.0, cv))  # Some variability is good
        
        # Factor 2: Reasonable intervals (not too fast, not too slow)
        if pattern.avg_interval < 0.5:  # Less than 500ms between messages
            interval_score = 0.1
        elif pattern.avg_interval < 2:
            interval_score = 0.5
        elif pattern.avg_interval < 30:
            interval_score = 1.0
        else:
            interval_score = 0.8
        
        # Factor 3: Burst behavior
        burst_score = max(0.0, 1.0 - (pattern.burst_count * 0.1))
        
        # Combined score
        score = (
            timing_score * self.TIMING_WEIGHT +
            interval_score * self.BURST_WEIGHT +
            burst_score * self.CONSISTENCY_WEIGHT
        )
        
        return max(self.MIN_RHYTHM_SCORE, min(self.MAX_RHYTHM_SCORE, score))
    
    async def _check_rhythm_violation(
        self,
        chat_id: int,
        user_id: int,
        pattern: MessagePattern,
        session: AsyncSession,
    ) -> Tuple[bool, str]:
        """
        Check if the current messaging pattern violates rhythm rules.
        
        Returns:
            Tuple of (is_allowed, reason)
        """
        now = datetime.utcnow()
        
        # Get chat settings
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings or not settings.automod_enabled:
            return True, ""
        
        # Count messages in window
        window_start = now - timedelta(seconds=settings.flood_window)
        recent_messages = [
            ts for ts in pattern.timestamps
            if ts >= window_start
        ]
        message_count = len(recent_messages)
        
        # Get adaptive threshold
        chat_state = self._get_chat_state(chat_id)
        threshold = self._calculate_adaptive_threshold(
            settings.spam_threshold,
            chat_state,
            pattern.rhythm_score,
        )
        
        # Check for flood
        if message_count > threshold:
            pattern.burst_count += 1
            
            # Check if it's a severe violation
            if message_count > threshold * 2:
                return False, f"Severe flood detected ({message_count} messages in {settings.flood_window}s)"
            
            # Apply rhythm penalty
            if pattern.rhythm_score < 0.3:
                return False, f"Abnormal messaging pattern (rhythm score: {pattern.rhythm_score:.2f})"
            
            # Warning level - allow but track
            if pattern.burst_count >= 3:
                return False, "Repeated burst behavior detected"
        
        # Reset burst count if enough time has passed
        if pattern.avg_interval > 10 and pattern.burst_count > 0:
            pattern.burst_count = max(0, pattern.burst_count - 1)
        
        return True, ""
    
    def _get_chat_state(self, chat_id: int) -> ChatActivityState:
        """Get or create chat activity state."""
        if chat_id not in self._chat_states:
            self._chat_states[chat_id] = ChatActivityState()
        
        state = self._chat_states[chat_id]
        state.hour_of_day = datetime.utcnow().hour
        state.day_of_week = datetime.utcnow().weekday()
        
        return state
    
    def _calculate_adaptive_threshold(
        self,
        base_threshold: int,
        chat_state: ChatActivityState,
        rhythm_score: float,
    ) -> float:
        """
        Calculate adaptive flood threshold based on context.
        
        During high activity, allow more messages.
        During quiet periods, be more strict.
        Users with good rhythm get more leeway.
        """
        # Base adjustment for chat activity
        if chat_state.messages_per_minute > 20:
            activity_multiplier = 1.5  # Busy chat, allow more
        elif chat_state.messages_per_minute > 10:
            activity_multiplier = 1.2
        else:
            activity_multiplier = 1.0
        
        # Rhythm bonus (good rhythm = higher threshold)
        rhythm_bonus = rhythm_score * 0.5
        
        # Combined threshold
        threshold = (base_threshold * activity_multiplier) + rhythm_bonus
        
        return max(base_threshold, threshold)
    
    async def _sync_to_database(
        self,
        chat_id: int,
        user_id: int,
        pattern: MessagePattern,
        session: AsyncSession,
    ) -> None:
        """Sync pattern data to database."""
        result = await session.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return
        
        member.rhythm_score = pattern.rhythm_score
        member.burst_count = pattern.burst_count
        if pattern.timestamps:
            member.last_message_time = pattern.timestamps[-1]
    
    async def get_rhythm_status(
        self,
        chat_id: int,
        user_id: int,
        session: AsyncSession,
    ) -> Dict:
        """
        Get detailed rhythm status for a user.
        
        Returns:
            Dictionary with rhythm metrics
        """
        result = await session.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return {"status": "unknown"}
        
        pattern = self._get_or_create_pattern(chat_id, user_id)
        
        return {
            "status": "good" if pattern.rhythm_score > 0.6 else ("warning" if pattern.rhythm_score > 0.3 else "bad"),
            "rhythm_score": round(pattern.rhythm_score, 3),
            "avg_interval": round(pattern.avg_interval, 2),
            "burst_count": pattern.burst_count,
            "recent_messages": len(pattern.timestamps),
            "trust_impact": "positive" if pattern.rhythm_score > 0.7 else ("neutral" if pattern.rhythm_score > 0.4 else "negative"),
        }
    
    async def reset_burst(
        self,
        chat_id: int,
        user_id: int,
    ) -> None:
        """Reset burst counter for a user (e.g., after timeout)."""
        async with self._lock:
            pattern = self._get_or_create_pattern(chat_id, user_id)
            pattern.burst_count = 0
    
    def cleanup_old_patterns(self, max_age_hours: int = 24) -> int:
        """
        Clean up old pattern data.
        
        Args:
            max_age_hours: Maximum age of patterns to keep
        
        Returns:
            Number of patterns cleaned
        """
        cutoff = datetime.utcnow() - timedelta(hours=max_age_hours)
        cleaned = 0
        
        for chat_id in list(self._user_patterns.keys()):
            for user_id in list(self._user_patterns[chat_id].keys()):
                pattern = self._user_patterns[chat_id][user_id]
                if pattern.last_updated < cutoff:
                    del self._user_patterns[chat_id][user_id]
                    cleaned += 1
            
            if not self._user_patterns[chat_id]:
                del self._user_patterns[chat_id]
        
        return cleaned


# Global conversation rhythm instance
conversation_rhythm = ConversationRhythm()


__all__ = ['ConversationRhythm', 'conversation_rhythm', 'MessagePattern', 'ChatActivityState']
