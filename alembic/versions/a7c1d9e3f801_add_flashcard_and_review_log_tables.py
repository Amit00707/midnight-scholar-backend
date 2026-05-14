"""Add flashcard and review_log tables

Revision ID: a7c1d9e3f801
Revises: 3b56f8df2f5d
Create Date: 2026-05-13 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c1d9e3f801'
down_revision: Union[str, None] = '3b56f8df2f5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # ── Flashcards table ──────────────────────────────────────
    op.create_table('flashcards',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('book_id', sa.String(length=255), nullable=False),
        sa.Column('source_page', sa.Integer(), nullable=True),
        sa.Column('front', sa.Text(), nullable=False),
        sa.Column('back', sa.Text(), nullable=False),
        sa.Column('tags', sa.String(length=500), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=True),
        sa.Column('ease_factor', sa.Float(), nullable=True),
        sa.Column('interval', sa.Integer(), nullable=True),
        sa.Column('repetitions', sa.Integer(), nullable=True),
        sa.Column('next_review', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('last_reviewed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_suspended', sa.Boolean(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_flashcards_id'), 'flashcards', ['id'], unique=False)
    op.create_index(op.f('ix_flashcards_user_id'), 'flashcards', ['user_id'], unique=False)
    op.create_index(op.f('ix_flashcards_book_id'), 'flashcards', ['book_id'], unique=False)

    # ── Review Logs table ─────────────────────────────────────
    op.create_table('review_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('flashcard_id', sa.Integer(), nullable=False),
        sa.Column('rating', sa.Integer(), nullable=False),
        sa.Column('time_spent_ms', sa.Integer(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('ease_factor_after', sa.Float(), nullable=True),
        sa.Column('interval_after', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['flashcard_id'], ['flashcards.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_review_logs_id'), 'review_logs', ['id'], unique=False)
    op.create_index(op.f('ix_review_logs_user_id'), 'review_logs', ['user_id'], unique=False)
    op.create_index(op.f('ix_review_logs_flashcard_id'), 'review_logs', ['flashcard_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_review_logs_flashcard_id'), table_name='review_logs')
    op.drop_index(op.f('ix_review_logs_user_id'), table_name='review_logs')
    op.drop_index(op.f('ix_review_logs_id'), table_name='review_logs')
    op.drop_table('review_logs')
    op.drop_index(op.f('ix_flashcards_book_id'), table_name='flashcards')
    op.drop_index(op.f('ix_flashcards_user_id'), table_name='flashcards')
    op.drop_index(op.f('ix_flashcards_id'), table_name='flashcards')
    op.drop_table('flashcards')
