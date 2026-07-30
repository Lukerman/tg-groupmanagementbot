"""
Trust Engine Service - Core reputation system.

Implements a sophisticated trust scoring mechanism that tracks member
behavior over time and influences moderation decisions dynamically.

This is NOT a simple warning system - it's a comprehensive behavior
tracking engine that considers:
- Message quality patterns
- Conversation rhythm
- Community engagement
- Rule compliance history
- Positive contributions
"""

import asyncio
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession
import logging
import json

from models import ChatMember, TimelineEvent, ChatSettings, AdaptivePermission
from database import db_manager
from utils.cache import get_cache

logger = logging.getLogger(__name__)


class TrustEngine:
    """
    Trust scoring and reputation management engine.
    
    Features:
    - Dynamic trust scoring based on behavior timeline
    - Automatic trust decay over time
    - Positive reinforcement tracking
    - Trust-based permission adjustments
    - Behavior pattern analysis
    """
    
    # Trust score boundaries
    MIN_TRUST = 0.0
    MAX_TRUST = 1.0
    DEFAULT_TRUST = 0.5
    
    # Trust adjustment values
    TRUST_JOIN_BONUS = 0.01
    TRUST_MESSAGE_BONUS = 0.001
    TRUST_WARNING_PENALTY = -0.05
    TRUST_MUTE_PENALTY = -0.10
    TRUST_POSITIVE_EVENT = 0.02
    TRUST_NEGATIVE_EVENT = -0.03
    
    # Decay settings
    DECAY_RATE_PER_HOUR = 0.001
    MIN_TRUST_DECAY = 0.3  # Trust won't decay below this
    
    def __init__(self):
        self._cache = get_cache()
        self._lock = asyncio.Lock()
    
    async def get_trust_score(
        self,
        chat_id: int,
        user_id: int,
        session: AsyncSession,
    ) -> float:
        """
        Get the current trust score for a member.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            session: Database session
        
        Returns:
            Trust score from 0.0 to 1.0
        """
        cache_key = f"trust:{chat_id}:{user_id}"
        cached = await self._cache.get(cache_key)
        if cached is not None:
            return cached
        
        # Get member from database
        result = await session.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return self.DEFAULT_TRUST
        
        return member.trust_score
    
    async def adjust_trust(
        self,
        chat_id: int,
        user_id: int,
        delta: float,
        reason: str,
        session: AsyncSession,
        event_type: Optional[str] = None,
        expires_at: Optional[datetime] = None,
    ) -> float:
        """
        Adjust a member's trust score.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            delta: Trust adjustment (positive or negative)
            reason: Reason for adjustment
            session: Database session
            event_type: Type of timeline event
            expires_at: When this adjustment expires
        
        Returns:
            New trust score
        """
        async with self._lock:
            # Get or create member
            result = await session.execute(
                select(ChatMember).where(
                    ChatMember.chat_id == chat_id,
                    ChatMember.user_id == user_id,
                )
            )
            member = result.scalar_one_or_none()
            
            if member is None:
                # Member doesn't exist yet, create minimal record
                member = ChatMember(
                    chat_id=chat_id,
                    user_id=user_id,
                    first_name="Unknown",
                    trust_score=self.DEFAULT_TRUST,
                )
                session.add(member)
            
            # Store old trust for timeline
            old_trust = member.trust_score
            
            # Apply adjustment with bounds
            new_trust = max(self.MIN_TRUST, min(self.MAX_TRUST, old_trust + delta))
            member.trust_score = new_trust
            member.updated_at = datetime.utcnow()
            
            # Create timeline event
            if event_type:
                category = "positive" if delta > 0 else ("negative" if delta < 0 else "neutral")
                timeline_event = TimelineEvent(
                    chat_id=chat_id,
                    member_id=member.id,
                    event_type=event_type,
                    event_category=category,
                    severity=abs(delta),
                    description=reason,
                    trust_delta=delta,
                    expires_at=expires_at,
                )
                session.add(timeline_event)
            
            # Update adaptive permissions based on trust
            await self._update_permissions_from_trust(
                chat_id, user_id, new_trust, session
            )
            
            # Invalidate cache
            cache_key = f"trust:{chat_id}:{user_id}"
            await self._cache.delete(cache_key)
            
            logger.info(
                f"Trust adjusted for {user_id} in {chat_id}: "
                f"{old_trust:.3f} -> {new_trust:.3f} ({delta:+.3f}) - {reason}"
            )
            
            return new_trust
    
    async def _update_permissions_from_trust(
        self,
        chat_id: int,
        user_id: int,
        trust_score: float,
        session: AsyncSession,
    ) -> None:
        """Update adaptive permissions based on trust score."""
        # Get settings for this chat
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings or not settings.trust_system_enabled:
            return
        
        # Get or create adaptive permission record
        result = await session.execute(
            select(AdaptivePermission).where(
                AdaptivePermission.chat_id == chat_id,
                AdaptivePermission.user_id == user_id,
            )
        )
        perm = result.scalar_one_or_none()
        
        if perm is None:
            perm = AdaptivePermission(
                chat_id=chat_id,
                user_id=user_id,
            )
            session.add(perm)
        
        # Adjust permissions based on trust
        min_for_links = settings.min_trust_for_links
        
        perm.can_send_links = trust_score >= min_for_links
        perm.trust_bonus = trust_score - self.DEFAULT_TRUST
        perm.last_adjusted = datetime.utcnow()
    
    async def apply_decay(self, chat_id: int, session: AsyncSession) -> int:
        """
        Apply trust decay to all members in a chat.
        
        Args:
            chat_id: Chat ID
            session: Database session
        
        Returns:
            Number of members affected
        """
        result = await session.execute(
            select(ChatSettings).where(ChatSettings.chat_id == chat_id)
        )
        settings = result.scalar_one_or_none()
        
        if not settings or not settings.trust_system_enabled:
            return 0
        
        decay_rate = settings.trust_decay_rate
        affected = 0
        
        # Get all members with trust above minimum
        members_result = await session.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.trust_score > self.MIN_TRUST_DECAY,
                ChatMember.status == 'member',
            )
        )
        members = members_result.scalars().all()
        
        for member in members:
            old_trust = member.trust_score
            new_trust = max(
                self.MIN_TRUST_DECAY,
                old_trust - decay_rate
            )
            
            if new_trust != old_trust:
                member.trust_score = new_trust
                member.updated_at = datetime.utcnow()
                affected += 1
                
                # Log decay event
                timeline_event = TimelineEvent(
                    chat_id=chat_id,
                    member_id=member.id,
                    event_type="trust_decay",
                    event_category="neutral",
                    severity=decay_rate,
                    description=f"Automatic trust decay: {decay_rate:.4f}",
                    trust_delta=-decay_rate,
                )
                session.add(timeline_event)
        
        return affected
    
    async def get_trust_timeline(
        self,
        chat_id: int,
        user_id: int,
        session: AsyncSession,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """
        Get the trust timeline for a member.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            session: Database session
            limit: Maximum events to return
        
        Returns:
            List of timeline events
        """
        result = await session.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return []
        
        events_result = await session.execute(
            select(TimelineEvent)
            .where(TimelineEvent.member_id == member.id)
            .order_by(TimelineEvent.occurred_at.desc())
            .limit(limit)
        )
        events = events_result.scalars().all()
        
        return [
            {
                "id": e.id,
                "type": e.event_type,
                "category": e.event_category,
                "severity": e.severity,
                "description": e.description,
                "trust_delta": e.trust_delta,
                "occurred_at": e.occurred_at.isoformat(),
                "is_active": e.is_active,
            }
            for e in events
        ]
    
    async def calculate_trust_from_timeline(
        self,
        chat_id: int,
        user_id: int,
        session: AsyncSession,
    ) -> float:
        """
        Recalculate trust score from timeline events.
        
        This can be used to verify or repair trust scores.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            session: Database session
        
        Returns:
            Calculated trust score
        """
        result = await session.execute(
            select(ChatMember).where(
                ChatMember.chat_id == chat_id,
                ChatMember.user_id == user_id,
            )
        )
        member = result.scalar_one_or_none()
        
        if member is None:
            return self.DEFAULT_TRUST
        
        # Get all active timeline events
        events_result = await session.execute(
            select(TimelineEvent).where(
                TimelineEvent.member_id == member.id,
                TimelineEvent.is_active == True,
                (TimelineEvent.expires_at == None) | 
                (TimelineEvent.expires_at > datetime.utcnow()),
            )
        )
        events = events_result.scalars().all()
        
        # Calculate trust from events
        trust = self.DEFAULT_TRUST
        now = datetime.utcnow()
        
        for event in events:
            # Apply time decay to older events
            age_hours = (now - event.occurred_at).total_seconds() / 3600
            decay_factor = max(0.1, 1.0 - (age_hours / 168))  # 1 week half-life
            
            trust += event.trust_delta * decay_factor
        
        # Clamp to valid range
        trust = max(self.MIN_TRUST, min(self.MAX_TRUST, trust))
        
        return trust
    
    async def award_positive_behavior(
        self,
        chat_id: int,
        user_id: int,
        behavior_type: str,
        session: AsyncSession,
    ) -> float:
        """
        Award trust for positive behavior.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            behavior_type: Type of positive behavior
            session: Database session
        
        Returns:
            New trust score
        """
        behaviors = {
            "helpful_message": self.TRUST_POSITIVE_EVENT,
            "active_participation": self.TRUST_MESSAGE_BONUS,
            "community_contribution": self.TRUST_POSITIVE_EVENT * 2,
            "rule_compliance_streak": self.TRUST_POSITIVE_EVENT * 1.5,
            "helping_newcomers": self.TRUST_POSITIVE_EVENT * 2,
            "quality_content": self.TRUST_POSITIVE_EVENT * 1.5,
        }
        
        delta = behaviors.get(behavior_type, self.TRUST_POSITIVE_EVENT)
        
        return await self.adjust_trust(
            chat_id=chat_id,
            user_id=user_id,
            delta=delta,
            reason=f"Positive behavior: {behavior_type}",
            session=session,
            event_type=f"positive_{behavior_type}",
        )
    
    async def penalize_negative_behavior(
        self,
        chat_id: int,
        user_id: int,
        behavior_type: str,
        session: AsyncSession,
        severity: float = 1.0,
    ) -> float:
        """
        Penalize trust for negative behavior.
        
        Args:
            chat_id: Chat ID
            user_id: User ID
            behavior_type: Type of negative behavior
            session: Database session
            severity: Severity multiplier (0.5 to 2.0)
        
        Returns:
            New trust score
        """
        behaviors = {
            "spam_detected": self.TRUST_NEGATIVE_EVENT,
            "rule_violation": self.TRUST_WARNING_PENALTY,
            "flood_detected": self.TRUST_NEGATIVE_EVENT * 1.5,
            "inappropriate_content": self.TRUST_WARNING_PENALTY * 1.5,
            "harassment": self.TRUST_WARNING_PENALTY * 2,
            "raid_participation": self.TRUST_MUTE_PENALTY,
        }
        
        base_delta = behaviors.get(behavior_type, self.TRUST_NEGATIVE_EVENT)
        delta = base_delta * max(0.5, min(2.0, severity))
        
        return await self.adjust_trust(
            chat_id=chat_id,
            user_id=user_id,
            delta=delta,
            reason=f"Negative behavior: {behavior_type} (severity: {severity})",
            session=session,
            event_type=f"negative_{behavior_type}",
        )


# Global trust engine instance
trust_engine = TrustEngine()


__all__ = ['TrustEngine', 'trust_engine']
