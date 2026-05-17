"""
Email Service — SendGrid Integration
====================================
Sends transactional emails via SendGrid API.
"""

import logging
from typing import Optional
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from app.core.config import settings

logger = logging.getLogger(__name__)


class EmailService:
    """SendGrid email service for transactional emails."""

    def __init__(self):
        self.api_key = settings.SENDGRID_API_KEY
        self.from_email = settings.SENDGRID_FROM_EMAIL
        self.from_name = "Midnight Scholar"
        self.is_configured = bool(self.api_key and self.api_key != "your-sendgrid-api-key")

    async def send_email(
        self,
        to_email: str,
        subject: str,
        body: str,
        html_body: Optional[str] = None,
    ) -> bool:
        """
        Send an email via SendGrid.

        Args:
            to_email: Recipient email address
            subject: Email subject line
            body: Plain text body
            html_body: HTML body (optional)

        Returns:
            bool: True if sent successfully, False otherwise
        """
        if not self.is_configured:
            logger.warning(f"SendGrid not configured. Would send email to {to_email}: {subject}")
            # Log the email that would be sent in development
            logger.debug(f"Mock email - To: {to_email}, Subject: {subject}, Body: {body[:100]}...")
            return True  # Return True in dev to not break flow

        try:
            import httpx

            # Build the email message
            message = MIMEMultipart("alternative")
            message["from"] = f"{self.from_name} <{self.from_email}>"
            message["to"] = to_email
            message["subject"] = subject

            # Add plain text part
            text_part = MIMEText(body, "plain", "utf-8")
            message.attach(text_part)

            # Add HTML part if provided
            if html_body:
                html_part = MIMEText(html_body, "html", "utf-8")
                message.attach(html_part)

            # Send via SendGrid API
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "personalizations": [
                            {"to": [{"email": to_email}]}
                        ],
                        "from": {
                            "email": self.from_email,
                            "name": self.from_name
                        },
                        "subject": subject,
                        "content": [
                            {
                                "type": "text/plain",
                                "value": body
                            }
                        ] + ([{
                            "type": "text/html",
                            "value": html_body
                        }] if html_body else [])
                    },
                    timeout=30.0,
                )

                if response.status_code in [200, 201, 202]:
                    logger.info(f"Email sent successfully to {to_email}")
                    return True
                else:
                    logger.error(f"SendGrid API error: {response.status_code} - {response.text}")
                    return False

        except ImportError:
            logger.error("httpx not installed. Install with: pip install httpx")
            return False
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    async def send_template_email(
        self,
        to_email: str,
        template_id: str,
        dynamic_data: dict,
    ) -> bool:
        """
        Send an email using a SendGrid dynamic template.

        Args:
            to_email: Recipient email address
            template_id: SendGrid template ID
            dynamic_data: Data to populate template

        Returns:
            bool: True if sent successfully
        """
        if not self.is_configured:
            logger.warning(f"SendGrid not configured. Would send template email to {to_email}")
            return True

        try:
            import httpx

            async with httpx.AsyncClient() as client:
                response = await client.post(
                    "https://api.sendgrid.com/v3/mail/send",
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "personalizations": [
                            {
                                "to": [{"email": to_email}],
                                "dynamic_template_data": dynamic_data
                            }
                        ],
                        "from": {
                            "email": self.from_email,
                            "name": self.from_name
                        },
                        "template_id": template_id,
                    },
                    timeout=30.0,
                )

                return response.status_code in [200, 201, 202]

        except Exception as e:
            logger.error(f"Failed to send template email: {e}")
            return False


# Singleton instance
email_service = EmailService()


# Convenience functions
async def send_email(to_email: str, subject: str, body: str, html_body: Optional[str] = None) -> bool:
    """Send a simple email."""
    return await email_service.send_email(to_email, subject, body, html_body)


async def send_welcome_email(to_email: str, user_name: str) -> bool:
    """Send welcome email to new users."""
    subject = "Welcome to Midnight Scholar!"
    body = f"""Hi {user_name},

Welcome to Midnight Scholar!

Your reading journey begins here. Explore thousands of books, create flashcards, and track your learning progress.

Get started:
1. Complete your profile
2. Select your interests
3. Start reading!

Happy reading!

- The Midnight Scholar Team
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background: linear-gradient(135deg, #D97706, #7C3AED); padding: 30px; text-align: center; color: white; border-radius: 10px 10px 0 0; }}
        .content {{ background: #f9f9f9; padding: 30px; border-radius: 0 0 10px 10px; }}
        .button {{ display: inline-block; background: #D97706; color: white; padding: 12px 24px; text-decoration: none; border-radius: 5px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>Welcome to Midnight Scholar!</h1>
        </div>
        <div class="content">
            <p>Hi {user_name},</p>
            <p>Welcome to Midnight Scholar!</p>
            <p>Your reading journey begins here. Explore thousands of books, create flashcards, and track your learning progress.</p>
            <p><strong>Get started:</strong></p>
            <ol>
                <li>Complete your profile</li>
                <li>Select your interests</li>
                <li>Start reading!</li>
            </ol>
            <a href="#" class="button">Start Reading</a>
            <p>Happy reading!</p>
            <p>- The Midnight Scholar Team</p>
        </div>
    </div>
</body>
</html>"""

    return await email_service.send_email(to_email, subject, body, html_body)


async def send_streak_reminder_email(to_email: str, user_name: str, streak_days: int) -> bool:
    """Send streak reminder email."""
    subject = f"Don't break your {streak_days}-day reading streak!"
    body = f"""Hey {user_name},

You have a {streak_days}-day reading streak going! Keep it up!

Just 10 minutes of reading today will keep your streak alive.

Keep reading!

- Midnight Scholar
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .streak {{ font-size: 48px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="streak">{streak_days} 🔥</div>
        <h2>Don't break your {streak_days}-day reading streak!</h2>
        <p>Hey {user_name},</p>
        <p>You have a {streak_days}-day reading streak going! Keep it up!</p>
        <p>Just 10 minutes of reading today will keep your streak alive.</p>
        <p>Keep reading!</p>
        <p>- Midnight Scholar</p>
    </div>
</body>
</html>"""

    return await email_service.send_email(to_email, subject, body, html_body)


async def send_achievement_email(to_email: str, user_name: str, badge_name: str, badge_icon: str) -> bool:
    """Send achievement/badge earned email."""
    subject = f"You earned: {badge_icon} {badge_name}!"
    body = f"""Hey {user_name}!

Congratulations! You just earned the "{badge_name}" badge!

Keep up the great work and continue your learning journey.

- Midnight Scholar
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
    <style>
        body {{ font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333; }}
        .container {{ max-width: 600px; margin: 0 auto; padding: 20px; }}
        .badge {{ font-size: 64px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="badge">{badge_icon}</div>
        <h2>You earned: {badge_name}!</h2>
        <p>Hey {user_name}!</p>
        <p>Congratulations! You just earned the "{badge_name}" badge!</p>
        <p>Keep up the great work and continue your learning journey.</p>
        <p>- Midnight Scholar</p>
    </div>
</body>
</html>"""

    return await email_service.send_email(to_email, subject, body, html_body)