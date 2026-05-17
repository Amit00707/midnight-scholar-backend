"""
Notification Models — Database Schema for Notifications
=========================================================
Stores notifications, preferences, and email templates.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, Enum
from sqlalchemy.orm import relationship
import enum

from app.database.session import Base


class NotificationChannelEnum(str, enum.Enum):
    EMAIL = "email"
    PUSH = "push"
    IN_APP = "in_app"


class NotificationTypeEnum(str, enum.Enum):
    STREAK_REMINDER = "streak_reminder"
    QUIZ_DUE = "quiz_due"
    ACHIEVEMENT = "achievement"
    MESSAGE = "message"
    READING_REMINDER = "reading_reminder"
    ANNOUNCEMENT = "announcement"
    CLASS_ASSIGNMENT = "class_assignment"
    COMMENT_REPLY = "comment_reply"


class Notification(Base):
    """User notifications (emails, push, in-app alerts)."""
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    notification_type = Column(Enum(NotificationTypeEnum), nullable=False)
    channel = Column(Enum(NotificationChannelEnum), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    recipient_email = Column(String(255), nullable=True)
    fcm_token = Column(String(500), nullable=True)
    is_read = Column(Boolean, default=False, index=True)
    external_id = Column(String(255), nullable=True)  # SendGrid/Firebase msg ID

    sent_at = Column(DateTime, nullable=True)
    read_at = Column(DateTime, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.id}: {self.notification_type.value} to {self.recipient_email or 'in-app'}>"


class NotificationPreference(Base):
    """User's notification preferences and frequency settings."""
    __tablename__ = "notification_preferences"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Channels (enabled/disabled)
    email_enabled = Column(Boolean, default=True)
    push_enabled = Column(Boolean, default=True)
    in_app_enabled = Column(Boolean, default=True)

    # Notification types (enabled/disabled)
    streak_reminders = Column(Boolean, default=True)
    quiz_alerts = Column(Boolean, default=True)
    achievements = Column(Boolean, default=True)
    messages = Column(Boolean, default=True)
    reading_reminders = Column(Boolean, default=True)
    announcements = Column(Boolean, default=True)
    class_assignments = Column(Boolean, default=True)
    comment_replies = Column(Boolean, default=True)

    # Quiet hours (no notifications between these times)
    quiet_hours_enabled = Column(Boolean, default=False)
    quiet_hours_start = Column(String(5), default="22:00")  # HH:MM format
    quiet_hours_end = Column(String(5), default="08:00")    # HH:MM format

    # Frequency settings
    digest_frequency = Column(String(50), default="daily")  # daily, weekly, never

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notification_preferences")

    def __repr__(self):
        return f"<NotificationPreference user_id={self.user_id}>"


class NotificationTemplate(Base):
    """Email/push/in-app message templates for different notification types."""
    __tablename__ = "notification_templates"

    id = Column(Integer, primary_key=True, index=True)
    notification_type = Column(Enum(NotificationTypeEnum), nullable=False, unique=True, index=True)

    # Email template
    email_subject = Column(String(255), nullable=False)
    email_body = Column(Text, nullable=False)

    # Push notification template
    push_title = Column(String(100), nullable=False)
    push_body = Column(String(240), nullable=False)

    # In-app notification template
    in_app_title = Column(String(100), nullable=False)
    in_app_body = Column(Text, nullable=False)

    # Variables that can be templated: {user_name}, {book_title}, {streak_count}, etc.
    # Example: "You've maintained a {streak_count} day reading streak!"

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<NotificationTemplate {self.notification_type.value}>"
