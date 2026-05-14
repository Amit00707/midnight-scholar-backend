"""
Social Routes — /comments /public-notes /groups /upvote
=========================================================
"""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.database.models.social import Comment, PublicNote, Group, GroupMember
from app.core.dependencies import get_current_user
from app.database.models.user import User
from app.schemas.social import CommentCreate, NoteCreate, GroupCreate

router = APIRouter()


@router.post("/posts")
async def create_post(payload: CommentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Post a thought/revelation to the social feed."""
    from app.database.models.progress import Highlight
    # Store as a highlight with book_id = "feed" to represent a general post
    highlight = Highlight(
        user_id=user.id,
        book_id=payload.book_id or "feed",
        page_number=0,
        text_content=payload.content,
    )
    db.add(highlight)
    await db.flush()
    return {"message": "Post created", "id": highlight.id}


@router.post("/comments")
async def create_comment(payload: CommentCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Post a comment on a book."""
    comment = Comment(user_id=user.id, book_id=payload.book_id, content=payload.content)
    db.add(comment)
    return {"message": "Comment posted"}


@router.post("/public-notes")
async def create_public_note(payload: NoteCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Share a public note from a page."""
    note = PublicNote(user_id=user.id, book_id=payload.book_id, page_number=payload.page_number, content=payload.content, is_public=payload.is_public)
    db.add(note)
    return {"message": "Public note created"}


@router.post("/groups")
async def create_group(payload: GroupCreate, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Create a new study group."""
    group = Group(name=payload.name, description=payload.description, created_by=user.id)
    db.add(group)
    await db.flush()
    member = GroupMember(group_id=group.id, user_id=user.id)
    db.add(member)
    return {"message": "Group created", "group_id": group.id}


@router.post("/upvote/{comment_id}")
async def upvote_comment(comment_id: int, user: User = Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    """Upvote a comment."""
    from sqlalchemy import select
    result = await db.execute(select(Comment).where(Comment.id == comment_id))
    comment = result.scalar_one_or_none()
    if comment:
        comment.upvotes += 1
    return {"message": "Upvoted"}


@router.get("/feed")
async def get_social_feed(db: AsyncSession = Depends(get_db)):
    """Get global community activity (highlights, reading progress)."""
    from sqlalchemy import select, desc
    from app.database.models.progress import Highlight
    from app.database.models.user import User

    # Fetch recent highlights
    result = await db.execute(
        select(Highlight, User.name)
        .join(User, Highlight.user_id == User.id)
        .order_by(desc(Highlight.created_at))
        .limit(20)
    )
    rows = result.all()

    feed = []
    for hl, user_name in rows:
        # In a fully fleshed out app, we would join with the books table
        # to get the exact title. Since book_id is an Open Library ID,
        # we will pass the ID and the frontend can fetch the title if needed,
        # or we can display the ID/placeholder for now.
        feed.append({
            "user": user_name,
            "action": "highlighted a passage",
            "book": f"Book {hl.book_id}",
            "time": hl.created_at.isoformat() if hl.created_at else "Recently",
            "quote": f'"{hl.text_content}"',
            "created_at": hl.created_at
        })

    # Sort descending
    feed.sort(key=lambda x: x["created_at"], reverse=True)
    return {"feed": feed}
