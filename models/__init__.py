"""
Database models for the Group Management Bot.

This module contains all SQLAlchemy ORM models with optimized schema design
for high-performance SQLite operations.
"""

from datetime import datetime, timedelta
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, BigInteger, Boolean, DateTime, 
    Float, Text, ForeignKey, Index, UniqueConstraint, event
)
from sqlalchemy.orm import relationship, declarative_base, Session
from sqlalchemy.ext.asyncio import AsyncAttrs

Base = declarative_base()


# ============================================================================
# CORE MODELS - Chat and User Foundation
# ============================================================================


class Chat(Base):
    """
    Represents a Telegram chat (group/superchannel).
    
    Stores configuration, settings, and state for each managed chat.
    """
    __tablename__ = 'chats'
    
    id = Column(BigInteger, primary_key=True)
    title = Column(String(256), nullable=False)
    username = Column(String(64), nullable=True)
    type = Column(String(32), nullable=False)  # group, supergroup, channel
    is_forum = Column(Boolean, default=False)
    
    # Configuration
    language = Column(String(8), default='en')
    timezone = Column(String(64), default='UTC')
    
    # State
    is_active = Column(Boolean, default=True)
    is_premium = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    settings = relationship("ChatSettings", back_populates="chat", uselist=False, cascade="all, delete-orphan")
    members = relationship("ChatMember", back_populates="chat", cascade="all, delete-orphan")
    events = relationship("ChatEvent", back_populates="chat", cascade="all, delete-orphan")
    
    __table_args__ = (
        Index('idx_chats_type', 'type'),
        Index('idx_chats_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<Chat(id={self.id}, title='{self.title}')>"


class ChatSettings(Base):
    """
    Stores all configurable settings for a chat.
    
    Separated from Chat for better normalization and flexibility.
    """
    __tablename__ = 'chat_settings'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey('chats.id', ondelete='CASCADE'), unique=True, nullable=False)
    
    # Welcome System
    welcome_enabled = Column(Boolean, default=True)
    welcome_message = Column(Text, nullable=True)
    welcome_delete_delay = Column(Integer, default=60)  # seconds
    
    # Security Settings
    anti_raid_enabled = Column(Boolean, default=True)
    raid_threshold = Column(Integer, default=10)  # joins per minute
    captcha_enabled = Column(Boolean, default=False)
    captcha_timeout = Column(Integer, default=300)  # seconds
    
    # Moderation
    automod_enabled = Column(Boolean, default=True)
    spam_threshold = Column(Integer, default=5)
    flood_window = Column(Integer, default=10)  # seconds
    link_limit = Column(Integer, default=3)
    mention_limit = Column(Integer, default=5)
    
    # Trust System
    trust_system_enabled = Column(Boolean, default=True)
    trust_decay_rate = Column(Float, default=0.01)  # per hour
    min_trust_for_links = Column(Float, default=0.3)
    
    # Activity Tracking
    activity_tracking_enabled = Column(Boolean, default=True)
    activity_window_hours = Column(Integer, default=24)
    
    # Permissions
    default_permissions_mask = Column(BigInteger, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="settings")
    
    __table_args__ = (
        Index('idx_settings_chat', 'chat_id'),
    )
    
    def __repr__(self):
        return f"<ChatSettings(chat_id={self.chat_id})>"


class ChatMember(Base):
    """
    Represents a member in a chat with their state and metrics.
    
    Core model for tracking member behavior, trust, and activity.
    """
    __tablename__ = 'chat_members'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    user_id = Column(BigInteger, nullable=False)
    username = Column(String(64), nullable=True)
    first_name = Column(String(256), nullable=False)
    last_name = Column(String(256), nullable=True)
    is_bot = Column(Boolean, default=False)
    is_premium = Column(Boolean, default=False)
    
    # Status
    status = Column(String(32), default='member')  # creator, administrator, member, left, kicked
    joined_at = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, nullable=True)
    
    # Trust System
    trust_score = Column(Float, default=0.5)
    trust_history = Column(Text, nullable=True)  # JSON-encoded history
    
    # Activity Metrics
    message_count = Column(Integer, default=0)
    activity_score = Column(Float, default=0.0)
    last_activity = Column(DateTime, nullable=True)
    
    # Moderation State
    warning_count = Column(Integer, default=0)
    is_muted = Column(Boolean, default=False)
    is_restricted = Column(Boolean, default=False)
    restriction_expires = Column(DateTime, nullable=True)
    
    # Conversation Rhythm (Anti-Flood)
    rhythm_score = Column(Float, default=1.0)
    last_message_time = Column(DateTime, nullable=True)
    burst_count = Column(Integer, default=0)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="members")
    timeline_events = relationship("TimelineEvent", back_populates="member", cascade="all, delete-orphan")
    milestones = relationship("MemberMilestone", back_populates="member", cascade="all, delete-orphan")
    
    __table_args__ = (
        UniqueConstraint('chat_id', 'user_id', name='uq_chat_member'),
        Index('idx_members_chat', 'chat_id'),
        Index('idx_members_user', 'user_id'),
        Index('idx_members_trust', 'trust_score'),
        Index('idx_members_status', 'status'),
    )
    
    def __repr__(self):
        return f"<ChatMember(chat_id={self.chat_id}, user_id={self.user_id})>"


# ============================================================================
# BEHAVIOR TIMELINE - Innovative Moderation Concept
# ============================================================================


class TimelineEvent(Base):
    """
    Represents an event in a member's behavior timeline.
    
    Instead of simple warnings, this creates a rich timeline of positive
    and negative behaviors that influence moderation decisions.
    """
    __tablename__ = 'timeline_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    member_id = Column(Integer, ForeignKey('chat_members.id', ondelete='CASCADE'), nullable=False)
    
    # Event Type
    event_type = Column(String(64), nullable=False)  # message, join, warning, praise, etc.
    event_category = Column(String(32), nullable=False)  # positive, neutral, negative
    
    # Event Data
    severity = Column(Float, default=0.0)  # -1.0 to 1.0
    description = Column(Text, nullable=True)
    context_data = Column(Text, nullable=True)  # JSON-encoded additional data
    
    # Impact
    trust_delta = Column(Float, default=0.0)
    expires_at = Column(DateTime, nullable=True)  # Events can expire
    is_active = Column(Boolean, default=True)
    
    # Metadata
    message_id = Column(BigInteger, nullable=True)
    moderator_id = Column(BigInteger, nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("ChatMember", back_populates="timeline_events")
    
    __table_args__ = (
        Index('idx_timeline_chat', 'chat_id'),
        Index('idx_timeline_member', 'member_id'),
        Index('idx_timeline_category', 'event_category'),
        Index('idx_timeline_occurred', 'occurred_at'),
        Index('idx_timeline_active', 'is_active'),
    )
    
    def __repr__(self):
        return f"<TimelineEvent(type={self.event_type}, severity={self.severity})>"


class MemberMilestone(Base):
    """
    Tracks significant achievements and milestones for members.
    
    Part of the positive reinforcement system.
    """
    __tablename__ = 'member_milestones'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    member_id = Column(Integer, ForeignKey('chat_members.id', ondelete='CASCADE'), nullable=False)
    
    # Milestone Info
    milestone_type = Column(String(64), nullable=False)
    milestone_name = Column(String(128), nullable=False)
    milestone_level = Column(Integer, default=1)
    
    # Progress
    current_value = Column(Integer, default=0)
    target_value = Column(Integer, nullable=False)
    is_completed = Column(Boolean, default=False)
    
    # Rewards
    reward_granted = Column(Boolean, default=False)
    reward_data = Column(Text, nullable=True)  # JSON-encoded reward info
    
    # Timestamps
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    member = relationship("ChatMember", back_populates="milestones")
    
    __table_args__ = (
        Index('idx_milestones_chat', 'chat_id'),
        Index('idx_milestones_member', 'member_id'),
        Index('idx_milestones_type', 'milestone_type'),
        Index('idx_milestones_completed', 'is_completed'),
    )
    
    def __repr__(self):
        return f"<MemberMilestone(type={self.milestone_type}, level={self.milestone_level})>"


# ============================================================================
# EVENT LOGGING - Comprehensive Audit Trail
# ============================================================================


class ChatEvent(Base):
    """
    Logs all significant events in a chat for auditing and analytics.
    """
    __tablename__ = 'chat_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, ForeignKey('chats.id', ondelete='CASCADE'), nullable=False)
    
    # Event Info
    event_type = Column(String(64), nullable=False)
    event_category = Column(String(32), nullable=False)  # system, moderation, member, admin
    
    # Actors
    actor_id = Column(BigInteger, nullable=True)
    actor_username = Column(String(64), nullable=True)
    target_id = Column(BigInteger, nullable=True)
    target_username = Column(String(64), nullable=True)
    
    # Details
    description = Column(Text, nullable=True)
    event_metadata = Column(Text, nullable=True)  # JSON-encoded extra data
    
    # Message Reference
    message_id = Column(BigInteger, nullable=True)
    
    # Timestamps
    occurred_at = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    # Relationships
    chat = relationship("Chat", back_populates="events")
    
    __table_args__ = (
        Index('idx_events_chat', 'chat_id'),
        Index('idx_events_type', 'event_type'),
        Index('idx_events_category', 'event_category'),
        Index('idx_events_occurred', 'occurred_at'),
    )
    
    def __repr__(self):
        return f"<ChatEvent(type={self.event_type}, chat_id={self.chat_id})>"


# ============================================================================
# ADAPTIVE PERMISSIONS - Dynamic Permission System
# ============================================================================


class AdaptivePermission(Base):
    """
    Stores adaptive permission states that change based on behavior.
    
    Unlike static permissions, these automatically adjust based on
    conversation rhythm, trust score, and activity patterns.
    """
    __tablename__ = 'adaptive_permissions'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    
    # Permission States
    can_send_messages = Column(Boolean, default=True)
    can_send_media = Column(Boolean, default=True)
    can_send_links = Column(Boolean, default=True)
    can_add_web_previews = Column(Boolean, default=True)
    can_send_polls = Column(Boolean, default=True)
    can_send_other_messages = Column(Boolean, default=True)
    can_change_info = Column(Boolean, default=False)
    can_invite_users = Column(Boolean, default=True)
    can_pin_messages = Column(Boolean, default=False)
    
    # Dynamic Modifiers
    cooldown_multiplier = Column(Float, default=1.0)
    rhythm_penalty = Column(Float, default=0.0)
    trust_bonus = Column(Float, default=0.0)
    
    # Zone State (Adaptive Cooling Zone)
    cooling_zone_active = Column(Boolean, default=False)
    cooling_zone_level = Column(Integer, default=0)
    cooling_zone_expires = Column(DateTime, nullable=True)
    
    # Timestamps
    last_adjusted = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('chat_id', 'user_id', name='uq_adaptive_perm'),
        Index('idx_adapt_perm_chat', 'chat_id'),
        Index('idx_adapt_perm_user', 'user_id'),
        Index('idx_adapt_perm_cooling', 'cooling_zone_active'),
    )
    
    def __repr__(self):
        return f"<AdaptivePermission(chat_id={self.chat_id}, user_id={self.user_id})>"


# ============================================================================
# INVITE REPUTATION - Track Invite Chain Quality
# ============================================================================


class InviteLink(Base):
    """
    Tracks invite links and their reputation based on invited member quality.
    """
    __tablename__ = 'invite_links'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    
    # Link Info
    invite_link = Column(Text, nullable=False)
    name = Column(String(128), nullable=True)
    creator_id = Column(BigInteger, nullable=True)
    
    # Reputation
    reputation_score = Column(Float, default=0.5)
    total_invited = Column(Integer, default=0)
    active_invited = Column(Integer, default=0)
    flagged_invited = Column(Integer, default=0)
    
    # Limits
    max_uses = Column(Integer, nullable=True)
    use_count = Column(Integer, default=0)
    expires_at = Column(DateTime, nullable=True)
    
    # State
    is_revoked = Column(Boolean, default=False)
    is_primary = Column(Boolean, default=False)
    
    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_invite_chat', 'chat_id'),
        Index('idx_invite_reputation', 'reputation_score'),
        Index('idx_invite_expires', 'expires_at'),
    )
    
    def __repr__(self):
        return f"<InviteLink(name='{self.name}', reputation={self.reputation_score})>"


class InviteChain(Base):
    """
    Tracks the chain of invites (who invited whom).
    """
    __tablename__ = 'invite_chains'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    
    inviter_id = Column(BigInteger, nullable=False)
    invitee_id = Column(BigInteger, nullable=False)
    invite_link_id = Column(Integer, ForeignKey('invite_links.id'), nullable=True)
    
    # Quality Tracking
    invitee_quality_score = Column(Float, default=0.5)
    invitee_is_active = Column(Boolean, default=True)
    invitee_flagged = Column(Boolean, default=False)
    
    # Timestamps
    invited_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_chain_chat', 'chat_id'),
        Index('idx_chain_inviter', 'inviter_id'),
        Index('idx_chain_invitee', 'invitee_id'),
    )
    
    def __repr__(self):
        return f"<InviteChain(inviter={self.inviter_id}, invitee={self.invitee_id})>"


# ============================================================================
# COMMUNITY HEALTH - Aggregate Metrics
# ============================================================================


class CommunityHealthSnapshot(Base):
    """
    Periodic snapshots of community health metrics.
    
    Used for analytics, trends, and proactive moderation.
    """
    __tablename__ = 'community_health_snapshots'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    
    # Health Metrics
    overall_health_score = Column(Float, default=0.5)
    activity_level = Column(Float, default=0.0)
    engagement_rate = Column(Float, default=0.0)
    toxicity_level = Column(Float, default=0.0)
    spam_level = Column(Float, default=0.0)
    
    # Member Stats
    total_members = Column(Integer, default=0)
    active_members = Column(Integer, default=0)
    new_members_today = Column(Integer, default=0)
    left_members_today = Column(Integer, default=0)
    
    # Message Stats
    messages_today = Column(Integer, default=0)
    avg_messages_per_member = Column(Float, default=0.0)
    
    # Trust Distribution
    avg_trust_score = Column(Float, default=0.5)
    high_trust_count = Column(Integer, default=0)
    low_trust_count = Column(Integer, default=0)
    
    # Snapshot Time
    snapshot_date = Column(DateTime, default=datetime.utcnow)
    period_start = Column(DateTime, nullable=False)
    period_end = Column(DateTime, nullable=False)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_health_chat', 'chat_id'),
        Index('idx_health_date', 'snapshot_date'),
        Index('idx_health_period', 'period_start', 'period_end'),
    )
    
    def __repr__(self):
        return f"<CommunityHealthSnapshot(chat_id={self.chat_id}, date={self.snapshot_date})>"


# ============================================================================
# SEASONAL EVENTS - Community Engagement System
# ============================================================================


class SeasonalEvent(Base):
    """
    Tracks seasonal events and community challenges.
    """
    __tablename__ = 'seasonal_events'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    
    # Event Info
    event_name = Column(String(128), nullable=False)
    event_type = Column(String(64), nullable=False)
    season_id = Column(String(64), nullable=True)
    
    # Progress
    start_date = Column(DateTime, nullable=False)
    end_date = Column(DateTime, nullable=False)
    is_active = Column(Boolean, default=True)
    is_completed = Column(Boolean, default=False)
    
    # Participation
    participant_count = Column(Integer, default=0)
    completion_count = Column(Integer, default=0)
    
    # Rewards
    rewards_distributed = Column(Integer, default=0)
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        Index('idx_seasonal_chat', 'chat_id'),
        Index('idx_seasonal_active', 'is_active'),
        Index('idx_seasonal_dates', 'start_date', 'end_date'),
    )
    
    def __repr__(self):
        return f"<SeasonalEvent(name='{self.event_name}', active={self.is_active})>"


class MemberBadge(Base):
    """
    Badges earned by members through achievements and participation.
    """
    __tablename__ = 'member_badges'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    chat_id = Column(BigInteger, nullable=False)
    user_id = Column(BigInteger, nullable=False)
    
    # Badge Info
    badge_id = Column(String(64), nullable=False)
    badge_name = Column(String(128), nullable=False)
    badge_tier = Column(String(16), default='bronze')  # bronze, silver, gold, platinum
    
    # Earning Info
    earned_reason = Column(Text, nullable=True)
    earned_context = Column(Text, nullable=True)  # JSON-encoded
    
    # Display
    is_equipped = Column(Boolean, default=False)
    is_hidden = Column(Boolean, default=False)
    
    # Timestamps
    earned_at = Column(DateTime, default=datetime.utcnow)
    
    __table_args__ = (
        UniqueConstraint('chat_id', 'user_id', 'badge_id', name='uq_member_badge'),
        Index('idx_badges_chat', 'chat_id'),
        Index('idx_badges_user', 'user_id'),
        Index('idx_badges_tier', 'badge_tier'),
    )
    
    def __repr__(self):
        return f"<MemberBadge(badge='{self.badge_name}', tier={self.badge_tier})>"


# ============================================================================
# DATABASE INITIALIZATION HELPERS
# ============================================================================


def create_all_tables(engine):
    """Create all database tables."""
    Base.metadata.create_all(engine)


def drop_all_tables(engine):
    """Drop all database tables."""
    Base.metadata.drop_all(engine)


# Export all models
__all__ = [
    'Base',
    'Chat',
    'ChatSettings',
    'ChatMember',
    'TimelineEvent',
    'MemberMilestone',
    'ChatEvent',
    'AdaptivePermission',
    'InviteLink',
    'InviteChain',
    'CommunityHealthSnapshot',
    'SeasonalEvent',
    'MemberBadge',
    'create_all_tables',
    'drop_all_tables',
]
