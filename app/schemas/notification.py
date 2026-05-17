"""
Notification Schemas — Pydantic Models for API Requests/Responses
===================================================================
Defines request/response payloads for notification endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field


class NotificationCreate(BaseModel):
    """Schema for creating a notification."""
    user_id: int
    notification_type: str  # from NotificationTypeEnum
    channel: str  # from NotificationChannelEnum
    title: str
    body: str
    recipient_email: Optional[str] = None
    fcm_token: Optional[str] = None


class NotificationUpdate(BaseModel):
    """Schema for updating a notification (mark as read, etc)."""
    is_read: Optional[bool] = None


class NotificationResponse(BaseModel):
    """Schema for returning notification in API response."""
    id: int
    user_id: int
    notification_type: str
    channel: str
    title: str
    body: str
    is_read: bool
    sent_at: Optional[datetime] = None
    read_at: Optional[datetime] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationListResponse(BaseModel):
    """Paginated list of notifications."""
    notifications: List[NotificationResponse]
    total: int
    skip: int
    limit: int


class UnreadCountResponse(BaseModel):
    """Response for unread notification count."""
    unread_count: int


class NotificationPreferenceResponse(BaseModel):
    """Schema for returning user's notification preferences."""
    id: int
    user_id: int

    # Channels
    email_enabled: bool
    push_enabled: bool
    in_app_enabled: bool

    # Notification types
    streak_reminders: bool
    quiz_alerts: bool
    achievements: bool
    messages: bool
    reading_reminders: bool
    announcements: bool
    class_assignments: bool
    comment_replies: bool

    # Quiet hours
    quiet_hours_enabled: bool
    quiet_hours_start: str
    quiet_hours_end: str

    # Digest frequency
    digest_frequency: str

    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class NotificationPreferenceUpdate(BaseModel):
    """Schema for updating notification preferences (partial or full update)."""
    # Channels
    email_enabled: Optional[bool] = None
    push_enabled: Optional[bool] = None
    in_app_enabled: Optional[bool] = None

    # Notification types
    streak_reminders: Optional[bool] = None
    quiz_alerts: Optional[bool] = None
    achievements: Optional[bool] = None
    messages: Optional[bool] = None
    reading_reminders: Optional[bool] = None
    announcements: Optional[bool] = None
    class_assignments: Optional[bool] = None
    comment_replies: Optional[bool] = None

    # Quiet hours
    quiet_hours_enabled: Optional[bool] = None
    quiet_hours_start: Optional[str] = None
    quiet_hours_end: Optional[str] = None

    # Digest frequency
    digest_frequency: Optional[str] = None


class NotificationTestRequest(BaseModel):
    """Schema for sending a test notification."""
    channel: str = Field(..., description="Channel: email, push, or in_app")
    title: str = Field(..., description="Notification title")
    body: str = Field(..., description="Notification body")
    fcm_token: Optional[str] = Field(None, description="FCM token for push notifications")
