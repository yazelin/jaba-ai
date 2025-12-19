"""使用者模型"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class User(Base):
    """使用者"""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_user_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    display_name: Mapped[Optional[str]] = mapped_column(String(128))
    picture_url: Mapped[Optional[str]] = mapped_column(Text)

    # 個人偏好 (JSONB)
    preferences: Mapped[dict] = mapped_column(JSONB, default=dict)

    # 封鎖狀態
    is_banned: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    banned_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯
    group_memberships = relationship("GroupMember", back_populates="user")
    group_admin_roles = relationship(
        "GroupAdmin",
        back_populates="user",
        foreign_keys="[GroupAdmin.user_id]",
    )
    orders = relationship("Order", back_populates="user")
    chat_messages = relationship("ChatMessage", back_populates="user")

    def __repr__(self) -> str:
        return f"<User {self.display_name or self.line_user_id}>"
