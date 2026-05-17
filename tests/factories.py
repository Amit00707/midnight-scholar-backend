"""
Factory Boy Factories — Test Data Generation
=============================================
Provides factories for creating test objects with realistic data.
"""

from datetime import datetime, timezone, timedelta
from typing import Optional

from factory import Factory, SubFactory, Sequence, LazyFunction, LazyAttribute
from factory.alchemy import SQLAlchemyModelFactory
from faker import Faker

from app.database.session import Base
from app.database.models.user import User, UserRole
from app.database.models.book import Book, Chapter, Tag
from app.database.models.progress import ReadingProgress, Bookmark, Highlight, Note
from app.database.models.notification import Notification, NotificationPreference, NotificationTemplate, NotificationChannelEnum, NotificationTypeEnum
from app.database.models.gamification import Badge, UserBadge, Points, Streak
from app.database.models.social import Comment, PublicNote, Group, GroupMember
from app.database.models.teacher import Classroom, StudentEnrollment, Assignment, Announcement
from app.database.models.flashcard import Flashcard, ReviewLog
from app.database.models.subscription import Plan, UserSubscription, BillingHistory

from app.core.security import hash_password


fake = Faker()


class UserFactory(SQLAlchemyModelFactory):
    """Factory for creating User instances."""
    class Meta:
        model = User

    email = Sequence(lambda n: f"user{n}@example.com")
    name = LazyFunction(fake.name)
    hashed_password = LazyFunction(lambda: hash_password("password123"))
    role = UserRole.student
    is_verified = True
    avatar_url = LazyFunction(lambda: fake.image_url())
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class TeacherFactory(UserFactory):
    """Factory for creating Teacher users."""
    role = UserRole.teacher
    email = Sequence(lambda n: f"teacher{n}@example.com")


class AdminFactory(UserFactory):
    """Factory for creating Admin users."""
    role = UserRole.admin
    email = Sequence(lambda n: f"admin{n}@example.com")


class BookFactory(SQLAlchemyModelFactory):
    """Factory for creating Book instances."""
    class Meta:
        model = Book

    title = LazyFunction(fake.sentence)
    author = LazyFunction(fake.name)
    description = LazyFunction(fake.paragraph)
    cover_url = LazyFunction(lambda: fake.image_url())
    pdf_s3_key = Sequence(lambda n: f"books/book-{n}.pdf")
    total_pages = LazyFunction(lambda: fake.random_int(min=50, max=500))
    difficulty = LazyFunction(lambda: fake.random_element(["beginner", "intermediate", "advanced"]))
    category = LazyFunction(lambda: fake.random_element(["Fiction", "Science", "History", "Technology"]))
    uploaded_by = 1  # Will be overridden
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class ChapterFactory(SQLAlchemyModelFactory):
    """Factory for creating Chapter instances."""
    class Meta:
        model = Chapter

    book_id = 1  # Will be overridden
    title = LazyFunction(fake.sentence)
    start_page = LazyFunction(lambda: fake.random_int(min=1, max=100))
    end_page = LazyAttribute(lambda obj: obj.start_page + fake.random_int(min=10, max=50))


class TagFactory(SQLAlchemyModelFactory):
    """Factory for creating Tag instances."""
    class Meta:
        model = Tag

    name = Sequence(lambda n: f"tag-{n}-{fake.word()}")


class ReadingProgressFactory(SQLAlchemyModelFactory):
    """Factory for creating ReadingProgress instances."""
    class Meta:
        model = ReadingProgress

    user_id = 1  # Will be overridden
    book_id = Sequence(lambda n: f"book-{n}")
    current_page = LazyFunction(lambda: fake.random_int(min=1, max=100))
    total_pages = LazyFunction(lambda: fake.random_int(min=100, max=500))
    percentage = LazyAttribute(lambda obj: (obj.current_page / obj.total_pages) * 100)
    time_spent_minutes = LazyFunction(lambda: fake.random_int(min=5, max=300))
    last_read_at = LazyFunction(lambda: datetime.now(timezone.utc))


class BookmarkFactory(SQLAlchemyModelFactory):
    """Factory for creating Bookmark instances."""
    class Meta:
        model = Bookmark

    user_id = 1  # Will be overridden
    book_id = Sequence(lambda n: f"book-{n}")
    page_number = LazyFunction(lambda: fake.random_int(min=1, max=500))
    label = LazyFunction(fake.sentence)
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class HighlightFactory(SQLAlchemyModelFactory):
    """Factory for creating Highlight instances."""
    class Meta:
        model = Highlight

    user_id = 1  # Will be overridden
    book_id = Sequence(lambda n: f"book-{n}")
    page_number = LazyFunction(lambda: fake.random_int(min=1, max=500))
    text_content = LazyFunction(fake.paragraph)
    color = LazyFunction(lambda: fake.random_element(["amber", "blue", "green", "red", "yellow"]))
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class NoteFactory(SQLAlchemyModelFactory):
    """Factory for creating Note instances."""
    class Meta:
        model = Note

    user_id = 1  # Will be overridden
    book_id = Sequence(lambda n: f"book-{n}")
    page_number = LazyFunction(lambda: fake.random_int(min=1, max=500))
    content = LazyFunction(fake.paragraph)
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class NotificationFactory(SQLAlchemyModelFactory):
    """Factory for creating Notification instances."""
    class Meta:
        model = Notification

    user_id = 1  # Will be overridden
    notification_type = LazyFunction(lambda: fake.random_element(list(NotificationTypeEnum)))
    channel = NotificationChannelEnum.IN_APP
    title = LazyFunction(fake.sentence)
    body = LazyFunction(fake.paragraph)
    recipient_email = LazyFunction(fake.email)
    fcm_token = LazyFunction(lambda: fake.sha1())
    is_read = False
    external_id = LazyFunction(lambda: fake.uuid4())
    sent_at = LazyFunction(lambda: datetime.now(timezone.utc))
    read_at = None
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class NotificationPreferenceFactory(SQLAlchemyModelFactory):
    """Factory for creating NotificationPreference instances."""
    class Meta:
        model = NotificationPreference

    user_id = 1  # Will be overridden
    email_enabled = True
    push_enabled = True
    in_app_enabled = True
    streak_reminders = True
    quiz_alerts = True
    achievements = True
    messages = True
    reading_reminders = True
    announcements = True
    class_assignments = True
    comment_replies = True
    quiet_hours_enabled = False
    quiet_hours_start = "22:00"
    quiet_hours_end = "08:00"
    digest_frequency = "daily"
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class BadgeFactory(SQLAlchemyModelFactory):
    """Factory for creating Badge instances."""
    class Meta:
        model = Badge

    name = Sequence(lambda n: f"badge-{n}-{fake.word()}")
    description = LazyFunction(fake.sentence)
    icon_url = LazyFunction(lambda: fake.image_url())
    requirement_type = LazyFunction(lambda: fake.random_element(["books_read", "streak_days", "points_earned"]))
    requirement_value = LazyFunction(lambda: fake.random_int(min=1, max=100))


class UserBadgeFactory(SQLAlchemyModelFactory):
    """Factory for creating UserBadge instances."""
    class Meta:
        model = UserBadge

    user_id = 1  # Will be overridden
    badge_id = 1  # Will be overridden
    earned_at = LazyFunction(lambda: datetime.now(timezone.utc))


class PointsFactory(SQLAlchemyModelFactory):
    """Factory for creating Points instances."""
    class Meta:
        model = Points

    user_id = 1  # Will be overridden
    amount = LazyFunction(lambda: fake.random_int(min=10, max=100))
    reason = LazyFunction(lambda: fake.random_element(["flashcard_correct", "book_finished", "quiz_passed"]))
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class StreakFactory(SQLAlchemyModelFactory):
    """Factory for creating Streak instances."""
    class Meta:
        model = Streak

    user_id = 1  # Will be overridden, unique constraint
    current_streak = LazyFunction(lambda: fake.random_int(min=0, max=365))
    longest_streak = LazyFunction(lambda: fake.random_int(min=0, max=365))
    last_activity_date = LazyFunction(lambda: datetime.now(timezone.utc) - timedelta(days=fake.random_int(min=0, max=7)))
    is_active = True


class CommentFactory(SQLAlchemyModelFactory):
    """Factory for creating Comment instances."""
    class Meta:
        model = Comment

    user_id = 1  # Will be overridden
    book_id = 1  # Will be overridden
    content = LazyFunction(fake.paragraph)
    upvotes = LazyFunction(lambda: fake.random_int(min=0, max=100))
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class PublicNoteFactory(SQLAlchemyModelFactory):
    """Factory for creating PublicNote instances."""
    class Meta:
        model = PublicNote

    user_id = 1  # Will be overridden
    book_id = 1  # Will be overridden
    page_number = LazyFunction(lambda: fake.random_int(min=1, max=500))
    content = LazyFunction(fake.paragraph)
    is_public = True
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class GroupFactory(SQLAlchemyModelFactory):
    """Factory for creating Group instances."""
    class Meta:
        model = Group

    name = LazyFunction(fake.sentence)
    description = LazyFunction(fake.paragraph)
    created_by = 1  # Will be overridden
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class GroupMemberFactory(SQLAlchemyModelFactory):
    """Factory for creating GroupMember instances."""
    class Meta:
        model = GroupMember

    group_id = 1  # Will be overridden
    user_id = 1  # Will be overridden
    joined_at = LazyFunction(lambda: datetime.now(timezone.utc))


class ClassroomFactory(SQLAlchemyModelFactory):
    """Factory for creating Classroom instances."""
    class Meta:
        model = Classroom

    name = LazyFunction(fake.sentence)
    description = LazyFunction(fake.paragraph)
    teacher_id = 1  # Will be overridden
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class StudentEnrollmentFactory(SQLAlchemyModelFactory):
    """Factory for creating StudentEnrollment instances."""
    class Meta:
        model = StudentEnrollment

    class_id = 1  # Will be overridden
    student_id = 1  # Will be overridden
    enrolled_at = LazyFunction(lambda: datetime.now(timezone.utc))


class AssignmentFactory(SQLAlchemyModelFactory):
    """Factory for creating Assignment instances."""
    class Meta:
        model = Assignment

    class_id = 1  # Will be overridden
    book_id = Sequence(lambda n: f"book-{n}")
    title = LazyFunction(fake.sentence)
    description = LazyFunction(fake.paragraph)
    due_date = LazyFunction(lambda: datetime.now(timezone.utc) + timedelta(days=7))
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class AnnouncementFactory(SQLAlchemyModelFactory):
    """Factory for creating Announcement instances."""
    class Meta:
        model = Announcement

    class_id = 1  # Will be overridden
    title = LazyFunction(fake.sentence)
    content = LazyFunction(fake.paragraph)
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))


class FlashcardFactory(SQLAlchemyModelFactory):
    """Factory for creating Flashcard instances."""
    class Meta:
        model = Flashcard

    user_id = 1  # Will be overridden
    book_id = Sequence(lambda n: f"book-{n}")
    source_page = LazyFunction(lambda: fake.random_int(min=1, max=500))
    front = LazyFunction(fake.sentence)
    back = LazyFunction(fake.paragraph)
    tags = LazyFunction(lambda: ",".join([fake.word() for _ in range(3)]))
    source = "manual"
    ease_factor = 2.5
    interval = 0
    repetitions = 0
    next_review = LazyFunction(lambda: datetime.now(timezone.utc))
    last_reviewed = None
    is_suspended = False
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
    updated_at = LazyFunction(lambda: datetime.now(timezone.utc))


class ReviewLogFactory(SQLAlchemyModelFactory):
    """Factory for creating ReviewLog instances."""
    class Meta:
        model = ReviewLog

    user_id = 1  # Will be overridden
    flashcard_id = 1  # Will be overridden
    rating = LazyFunction(lambda: fake.random_int(min=0, max=3))
    time_spent_ms = LazyFunction(lambda: fake.random_int(min=1000, max=60000))
    reviewed_at = LazyFunction(lambda: datetime.now(timezone.utc))
    ease_factor_after = 2.5
    interval_after = 1


class PlanFactory(SQLAlchemyModelFactory):
    """Factory for creating Plan instances."""
    class Meta:
        model = Plan

    name = Sequence(lambda n: f"plan-{n}")
    price_monthly = LazyFunction(lambda: fake.random_int(min=99, max=999))
    price_yearly = LazyFunction(lambda: fake.random_int(min=900, max=9900))
    max_books = LazyFunction(lambda: fake.random_int(min=5, max=100))
    ai_queries_per_day = LazyFunction(lambda: fake.random_int(min=10, max=1000))
    features = '["feature1", "feature2", "feature3"]'


class UserSubscriptionFactory(SQLAlchemyModelFactory):
    """Factory for creating UserSubscription instances."""
    class Meta:
        model = UserSubscription

    user_id = 1  # Will be overridden
    plan_id = 1  # Will be overridden
    stripe_subscription_id = LazyFunction(lambda: f"sub_{fake.sha1()}")
    is_active = True
    started_at = LazyFunction(lambda: datetime.now(timezone.utc))
    expires_at = LazyFunction(lambda: datetime.now(timezone.utc) + timedelta(days=30))


class BillingHistoryFactory(SQLAlchemyModelFactory):
    """Factory for creating BillingHistory instances."""
    class Meta:
        model = BillingHistory

    user_id = 1  # Will be overridden
    amount = LazyFunction(lambda: fake.random_int(min=99, max=9999))
    currency = "INR"
    status = "succeeded"
    stripe_payment_id = LazyFunction(lambda: f"pi_{fake.sha1()}")
    created_at = LazyFunction(lambda: datetime.now(timezone.utc))
