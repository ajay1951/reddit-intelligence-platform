"""create_ingestion_runs_table

Revision ID: 1278fe2e2b50
Revises: 9b69eb1c7c92
Create Date: 2026-10-16 15:33:43.679787

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '1278fe2e2b50'
down_revision: Union[str, None] = '9b69eb1c7c92'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('ingestion_runs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_id', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('subreddits', postgresql.ARRAY(sa.String()), nullable=False),
        sa.Column('posts_ingested', sa.Integer(), nullable=False),
        sa.Column('comments_ingested', sa.Integer(), nullable=False),
        sa.Column('provider_used', sa.String(length=50), nullable=False),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_ingestion_runs_started_at', 'ingestion_runs', ['started_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_ingestion_runs_started_at', table_name='ingestion_runs')
    op.drop_table('ingestion_runs')

    # ### end Alembic commands ###
