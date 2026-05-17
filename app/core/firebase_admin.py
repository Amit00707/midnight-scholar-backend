"""
Firebase Admin SDK — Push Notifications via Cloud Messaging
==============================================================
Initializes Firebase Admin SDK and provides functions for sending push notifications.
"""

import json
import logging
from typing import Optional, Dict, Any
from app.core.config import settings

logger = logging.getLogger(__name__)

# Lazy global — initialized on first use
_firebase_app = None


def init_firebase():
    """
    Initialize Firebase Admin SDK from FIREBASE_CREDENTIALS_JSON config.
    Returns None if credentials not configured (graceful degradation).
    """
    global _firebase_app

    if _firebase_app is not None:
        return _firebase_app

    if not settings.FIREBASE_CREDENTIALS_JSON or settings.FIREBASE_CREDENTIALS_JSON.startswith("your-"):
        logger.warning("Firebase credentials not configured. Push notifications disabled.")
        return None

    try:
        import firebase_admin
        from firebase_admin import credentials, messaging

        # Parse JSON credentials
        creds_dict = json.loads(settings.FIREBASE_CREDENTIALS_JSON)
        cred = credentials.Certificate(creds_dict)

        # Initialize app
        _firebase_app = firebase_admin.initialize_app(cred)
        logger.info("✓ Firebase Admin SDK initialized successfully")
        return _firebase_app

    except ImportError:
        logger.warning("firebase_admin SDK not installed. Install via: pip install firebase-admin")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Invalid Firebase credentials JSON: {e}")
        return None
    except Exception as e:
        logger.error(f"Failed to initialize Firebase: {e}")
        return None


async def send_push_notification(
    fcm_token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
    badge: Optional[str] = None,
) -> bool:
    """
    Send a push notification via Firebase Cloud Messaging.

    Args:
        fcm_token: FCM token of the recipient device
        title: Notification title
        body: Notification body
        data: Optional key-value data payload (max 4KB)
        badge: Optional badge count for iOS

    Returns:
        True if sent successfully, False otherwise
    """
    try:
        from firebase_admin import messaging

        app = init_firebase()
        if app is None:
            logger.info(f"Firebase not initialized. Notification not sent: {title}")
            return False

        # Build notification
        notification = messaging.Notification(title=title, body=body)

        # Build message
        message_dict = {
            "token": fcm_token,
            "notification": notification,
        }

        # Add optional data payload
        if data:
            message_dict["data"] = data

        # Add badge for iOS
        if badge:
            message_dict["webpush"] = {
                "notification": {"badge": badge}
            }

        message = messaging.Message(**message_dict)

        # Send
        response = messaging.send(message)
        logger.info(f"✓ Push notification sent: {response}")
        return True

    except ImportError:
        logger.warning("firebase_admin not installed; skipping push notification")
        return False
    except Exception as e:
        logger.error(f"Failed to send push notification: {e}")
        return False


async def send_multicast_push_notification(
    fcm_tokens: list,
    title: str,
    body: str,
    data: Optional[Dict[str, str]] = None,
) -> Dict[str, Any]:
    """
    Send push notifications to multiple devices.

    Args:
        fcm_tokens: List of FCM tokens
        title: Notification title
        body: Notification body
        data: Optional key-value data payload

    Returns:
        Dict with success_count, failure_count, and errors
    """
    if not fcm_tokens:
        return {"success_count": 0, "failure_count": 0, "errors": []}

    try:
        from firebase_admin import messaging

        app = init_firebase()
        if app is None:
            logger.info(f"Firebase not initialized. Multicast notification not sent: {title}")
            return {
                "success_count": 0,
                "failure_count": len(fcm_tokens),
                "errors": ["Firebase not initialized"],
            }

        notification = messaging.Notification(title=title, body=body)
        message_dict = {"notification": notification}

        if data:
            message_dict["data"] = data

        message = messaging.MulticastMessage(
            tokens=fcm_tokens,
            **message_dict
        )

        response = messaging.send_multicast(message)
        logger.info(
            f"✓ Multicast sent: {response.success_count} succeeded, "
            f"{response.failure_count} failed"
        )

        return {
            "success_count": response.success_count,
            "failure_count": response.failure_count,
            "errors": [str(err) for err in response.errors] if response.errors else [],
        }

    except ImportError:
        logger.warning("firebase_admin not installed; skipping multicast notification")
        return {
            "success_count": 0,
            "failure_count": len(fcm_tokens),
            "errors": ["firebase_admin not installed"],
        }
    except Exception as e:
        logger.error(f"Failed to send multicast push notifications: {e}")
        return {
            "success_count": 0,
            "failure_count": len(fcm_tokens),
            "errors": [str(e)],
        }
