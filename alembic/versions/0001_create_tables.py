"""create initial tables

Revision ID: 0001_create_tables
Revises: 
Create Date: 2026-06-02
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '0001_create_tables'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'subreddits',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('name', sa.String(255), nullable=False, unique=True),
        sa.Column('url', sa.String(1024), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )

    op.create_table(
        'posts',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('title', sa.String(1024), nullable=False),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('subreddit_id', sa.Integer(), sa.ForeignKey('subreddits.id'), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('comments_count', sa.Integer(), nullable=True),
        sa.Column('url', sa.String(2048), nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('scraped_at', sa.DateTime(), nullable=True),
        sa.UniqueConstraint('url', name='uq_posts_url'),
    )

    op.create_table(
        'comments',
        sa.Column('id', sa.BigInteger(), primary_key=True),
        sa.Column('post_id', sa.Integer(), sa.ForeignKey('posts.id'), nullable=False),
        sa.Column('author', sa.String(255), nullable=True),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
    )


def downgrade() -> None:
    op.drop_table('comments')
    op.drop_table('posts')
    op.drop_table('subreddits')
