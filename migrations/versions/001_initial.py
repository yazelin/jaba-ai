"""Initial migration

Revision ID: 001
Revises:
Create Date: 2024-12-12

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Users
    op.create_table(
        'users',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('line_user_id', sa.String(64), unique=True, nullable=False, index=True),
        sa.Column('display_name', sa.String(128), nullable=True),
        sa.Column('picture_url', sa.Text, nullable=True),
        sa.Column('preferences', postgresql.JSONB, default={}),
        sa.Column('is_banned', sa.Boolean, nullable=False, server_default='false'),
        sa.Column('banned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Groups
    op.create_table(
        'groups',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('line_group_id', sa.String(50), unique=True, nullable=False, index=True),
        sa.Column('name', sa.String(100), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('group_code', sa.String(64), nullable=True, index=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('activated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('activated_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Group Applications
    op.create_table(
        'group_applications',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('line_group_id', sa.String(50), nullable=False),
        sa.Column('group_name', sa.String(256), nullable=True),
        sa.Column('contact_info', sa.Text, nullable=True),
        sa.Column('group_code', sa.String(64), nullable=True),
        sa.Column('status', sa.String(20), default='pending'),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('review_note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Group Members
    op.create_table(
        'group_members',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('joined_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_group_member'),
    )

    # Group Admins
    op.create_table(
        'group_admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('granted_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('granted_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('group_id', 'user_id', name='uq_group_admin'),
    )

    # Stores
    op.create_table(
        'stores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('phone', sa.String(100), nullable=True),
        sa.Column('address', sa.String(200), nullable=True),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('is_active', sa.Boolean, default=True),
        sa.Column('scope', sa.String(16), server_default='global', nullable=False),
        sa.Column('group_code', sa.String(64), nullable=True),
        sa.Column('created_by_type', sa.String(16), server_default='admin', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Menus
    op.create_table(
        'menus',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stores.id'), unique=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Menu Categories
    op.create_table(
        'menu_categories',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('menu_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('menus.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('sort_order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Menu Items
    op.create_table(
        'menu_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('category_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('menu_categories.id'), nullable=False),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('price', sa.Numeric(10, 2), nullable=False),
        sa.Column('description', sa.Text, nullable=True),
        sa.Column('variants', postgresql.JSONB, default=[]),
        sa.Column('promo', postgresql.JSONB, nullable=True),
        sa.Column('is_available', sa.Boolean, default=True),
        sa.Column('sort_order', sa.Integer, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Group Today Stores
    op.create_table(
        'group_today_stores',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id'), nullable=False),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stores.id'), nullable=False),
        sa.Column('date', sa.Date, nullable=False, server_default=sa.func.current_date()),
        sa.Column('set_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('set_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('group_id', 'store_id', 'date', name='uq_group_today_store'),
    )

    # Order Sessions
    op.create_table(
        'order_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id'), nullable=False),
        sa.Column('status', sa.String(32), default='ordering'),
        sa.Column('started_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('ended_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Orders
    op.create_table(
        'orders',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('order_sessions.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('store_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('stores.id'), nullable=False),
        sa.Column('total_amount', sa.Numeric(10, 2), default=0),
        sa.Column('payment_status', sa.String(32), default='unpaid'),
        sa.Column('paid_amount', sa.Numeric(10, 2), default=0),
        sa.Column('paid_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Order Items
    op.create_table(
        'order_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('order_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('orders.id'), nullable=False),
        sa.Column('menu_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('menu_items.id'), nullable=True),
        sa.Column('name', sa.String(100), nullable=False),
        sa.Column('quantity', sa.Integer, default=1),
        sa.Column('unit_price', sa.Numeric(10, 2), nullable=False),
        sa.Column('subtotal', sa.Numeric(10, 2), nullable=False),
        sa.Column('options', postgresql.JSONB, default={}),
        sa.Column('note', sa.Text, nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Chat Messages
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('group_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('groups.id'), nullable=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('role', sa.String(20), nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('order_sessions.id'), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), index=True),
    )

    # AI Prompts
    op.create_table(
        'ai_prompts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(100), unique=True, nullable=False),
        sa.Column('content', sa.Text, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Super Admins
    op.create_table(
        'super_admins',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('username', sa.String(64), unique=True, nullable=False),
        sa.Column('password_hash', sa.String(256), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), onupdate=sa.func.now()),
    )

    # Security Logs
    op.create_table(
        'security_logs',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('line_user_id', sa.String(64), nullable=False),
        sa.Column('display_name', sa.String(128), nullable=True),
        sa.Column('line_group_id', sa.String(64), nullable=True),
        sa.Column('original_message', sa.Text, nullable=False),
        sa.Column('sanitized_message', sa.Text, nullable=False),
        sa.Column('trigger_reasons', postgresql.JSONB, nullable=False),
        sa.Column('context_type', sa.String(16), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Create indexes
    op.create_index('ix_chat_messages_group_id', 'chat_messages', ['group_id'])
    op.create_index('ix_chat_messages_user_id', 'chat_messages', ['user_id'])
    op.create_index('ix_order_sessions_group_id', 'order_sessions', ['group_id'])
    op.create_index('ix_orders_session_id', 'orders', ['session_id'])
    op.create_index('ix_orders_user_id', 'orders', ['user_id'])
    op.create_index('ix_stores_scope', 'stores', ['scope'])
    op.create_index('ix_stores_group_code', 'stores', ['group_code'])
    op.create_index('ix_security_logs_line_user_id', 'security_logs', ['line_user_id'])
    op.create_index('ix_security_logs_line_group_id', 'security_logs', ['line_group_id'])
    op.create_index('ix_security_logs_created_at', 'security_logs', ['created_at'])


def downgrade() -> None:
    op.drop_table('security_logs')
    op.drop_table('super_admins')
    op.drop_table('ai_prompts')
    op.drop_table('chat_messages')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('order_sessions')
    op.drop_table('group_today_stores')
    op.drop_table('menu_items')
    op.drop_table('menu_categories')
    op.drop_table('menus')
    op.drop_table('stores')
    op.drop_table('group_admins')
    op.drop_table('group_members')
    op.drop_table('group_applications')
    op.drop_table('groups')
    op.drop_table('users')
