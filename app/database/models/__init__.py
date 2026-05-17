# Database models package — import all models here so Alembic can detect them.
from app.database.models.user import User, UserSession, UserRole
from app.database.models.book import Book, Chapter, Tag, BookVersion, AuditLog
from app.database.models.progress import ReadingProgress, Bookmark, Highlight, Note, ReadingGaps, RevisionItem
from app.database.models.social import Comment, PublicNote, Group, GroupMember
from app.database.models.gamification import Badge, UserBadge, Points, Streak
from app.database.models.subscription import Plan, UserSubscription, BillingHistory
from app.database.models.teacher import Classroom, StudentEnrollment, Assignment, Announcement
from app.database.models.flashcard import Flashcard, ReviewLog
from app.database.models.notification import Notification, NotificationPreference, NotificationTemplate
