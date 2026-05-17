"""
Push Notification Service — Firebase Cloud Messaging (FCM)
==========================================================
Sends push notifications via Firebase FCM.
"""

import logging
import json
from typing import Optional, Dict, Any

from app.core.config import settings

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Firebase Cloud Messaging service for push notifications."""

    def __init__(self):
        self.credentials_json = settings.FIREBASE_CREDENTIALS_JSON
        self.is_configured = bool(
            self.credentials_json
            and self.credentials_json != "your-firebase-credentials-json"
            and self.credentials_json != ""
        )
        self._firebase_admin = None

    def _get_firebase_admin(self):
        """Lazy load Firebase Admin SDK."""
        if self._firebase_admin is not None:
            return self._firebase_admin

        if not self.is_configured:
            logger.warning("Firebase not configured - push notifications disabled")
            return None

        try:
            import firebase_admin
            from firebase_admin import credentials

            # Parse the JSON credentials
            cred_dict = json.loads(self.credentials_json)
            cred = credentials.Certificate(cred_dict)

            # Initialize Firebase app
            self._firebase_admin = firebase_admin.initialize_app(cred)
            logger.info("Firebase Admin SDK initialized successfully")
            return self._firebase_admin

        except json.JSONDecodeError as e:
            logger.error(f"Invalid Firebase credentials JSON: {e}")
            return None
        except ImportError:
            logger.error("firebase-admin not installed. Install with: pip install firebase-admin")
            return None
        except Exception as e:
            logger.error(f"Failed to initialize Firebase: {e}")
            return None

    async def send_push(
        self,
        fcm_token: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
        image_url: Optional[str] = None,
    ) -> bool:
        """
        Send a push notification via FCM.

        Args:
            fcm_token: Firebase Cloud Messaging token for the device
            title: Notification title
            body: Notification body text
            data: Optional data payload (key-value pairs)
            image_url: Optional image URL for notification

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning(f"Firebase not configured. Would send push to {fcm_token[:20]}...: {title}")
            # Log the notification in development
            logger.debug(f"Mock push - Title: {title}, Body: {body}")
            return True  # Return True in dev to not break flow

        firebase_app = self._get_firebase_admin()
        if not firebase_app:
            logger.error("Firebase not initialized - cannot send push notification")
            return False

        try:
            from firebase_admin import messaging

            # Build the message
            message = messaging.Message(
                notification=messaging.Notification(
                    title=title,
                    body=body,
                    image=image_url,
                ),
                data=data or {},
                token=fcm_token,
            )

            # Send the message
            response = messaging.send(message)
            logger.info(f"Push notification sent successfully: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send push notification: {e}")
            return False

    async def send_to_topic(
        self,
        topic: str,
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Send push notification to all devices subscribed to a topic."""
        if not self.is_configured:
            logger.warning(f"Firebase not configured. Would send to topic: {topic}")
            return True

        firebase_app = self._get_firebase_admin()
        if not firebase_app:
            return False

        try:
            from firebase_admin import messaging

            message = messaging.Message(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                topic=topic,
            )

            response = messaging.send(message)
            logger.info(f"Push to topic {topic} sent: {response}")
            return True

        except Exception as e:
            logger.error(f"Failed to send to topic: {e}")
            return False

    async def send_to_multiple_tokens(
        self,
        tokens: list[str],
        title: str,
        body: str,
        data: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Send push notification to multiple devices.

        Returns:
            dict with success_count and failed_tokens
        """
        if not self.is_configured:
            logger.warning(f"Firebase not configured. Would send to {len(tokens)} tokens")
            return {"success_count": len(tokens), "failed_tokens": []}

        firebase_app = self._get_firebase_admin()
        if not firebase_app:
            return {"success_count": 0, "failed_tokens": tokens}

        try:
            from firebase_admin import messaging

            # Create multicast message
            message = messaging.MulticastMessage(
                notification=messaging.Notification(title=title, body=body),
                data=data or {},
                tokens=tokens,
            )

            # Send to all tokens
            response = messaging.send_multicast(message)

            logger.info(f"Sent to {response.success_count} devices, {response.failure_count} failed")

            # Get failed tokens
            failed_tokens = []
            for idx, error in enumerate(response.errors):
                if idx < len(tokens):
                    failed_tokens.append(tokens[idx])
                logger.error(f"Failed to send to token {idx}: {error}")

            return {
                "success_count": response.success_count,
                "failed_tokens": failed_tokens,
            }

        except Exception as e:
            logger.error(f"Failed to send multicast: {e}")
            return {"success_count": 0, "failed_tokens": tokens}


# Singleton instance
push_service = PushNotificationService()


# Convenience functions
async def send_push(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> bool:
    """Send a simple push notification."""
    return await push_service.send_push(fcm_token, title, body, data)


async def send_streak_reminder_push(fcm_token: str, streak_days: int) -> bool:
    """Send streak reminder push notification."""
    title = f"🔥 Keep your {streak_days}-day streak alive!"
    body = "Just 10 minutes of reading today will keep your streak going."
    data = {"type": "streak_reminder", "streak_days": str(streak_days)}
    return await push_service.send_push(fcm_token, title, body, data)


async def send_achievement_push(fcm_token: str, badge_name: str, badge_icon: str) -> bool:
    """Send achievement earned push notification."""
    title = f"🎉 You earned: {badge_icon} {badge_name}!"
    body = "Check your profile to see your new badge!"
    data = {"type": "achievement", "badge_name": badge_name}
    return await push_service.send_push(fcm_token, title, body, data)


async def send_flashcard_due_push(fcm_token: str, due_count: int) -> bool:
    """Send flashcard due reminder push notification."""
    title = f"📚 You have {due_count} flashcards to review!"
    body = "Keep your memory sharp with daily reviews."
    data = {"type": "flashcard_due", "due_count": str(due_count)}
    return await push_service.send_push(fcm_token, title, body, data)


async def send_class_assignment_push(fcm_token: str, class_name: str, book_title: str, due_date: str) -> bool:
    """Send class assignment push notification."""
    title = f"📖 New assignment in {class_name}"
    body = f"Read {book_title} - Due: {due_date}"
    data = {
        "type": "class_assignment",
        "class_name": class_name,
        "book_title": book_title,
        "due_date": due_date,
    }
    return await push_service.send_push(fcm_token, title, body, data)