"""add ai_logs table

Revision ID: 003
Revises: 002
Create Date: 2025-12-19

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '003'
down_revision: Union[str, None] = '002'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ai_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id', ondelete='SET NULL'), nullable=True, index=True),
        sa.Column('model', sa.String(32), nullable=False),
        sa.Column('input_prompt', sa.Text, nullable=False),
        sa.Column('raw_response', sa.Text, nullable=False),
        sa.Column('parsed_message', sa.Text, nullable=True),
        sa.Column('parsed_actions', postgresql.JSONB, nullable=True),
        sa.Column('success', sa.Boolean, nullable=False, default=True),
        sa.Column('duration_ms', sa.Integer, nullable=True),
        sa.Column('input_tokens', sa.Integer, nullable=True),
        sa.Column('output_tokens', sa.Integer, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )


def downgrade() -> None:
    op.drop_table('ai_logs')
