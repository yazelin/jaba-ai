"""群組相關模型"""
import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base

if TYPE_CHECKING:
    from app.models.user import User


class Group(Base):
    """LINE 群組"""

    __tablename__ = "groups"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_group_id: Mapped[str] = mapped_column(
        String(64), unique=True, nullable=False, index=True
    )
    name: Mapped[Optional[str]] = mapped_column(String(256))
    description: Mapped[Optional[str]] = mapped_column(Text)
    group_code: Mapped[Optional[str]] = mapped_column(String(64), index=True)

    # 狀態: pending, active, suspended
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)

    # 啟用資訊
    activated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    activated_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯（cascade 確保刪除群組時連帶刪除相關資料）
    activator = relationship("User", foreign_keys=[activated_by])
    members = relationship("GroupMember", back_populates="group", cascade="all, delete-orphan")
    admins = relationship("GroupAdmin", back_populates="group", cascade="all, delete-orphan")
    today_stores = relationship("GroupTodayStore", back_populates="group", cascade="all, delete-orphan")
    order_sessions = relationship("OrderSession", back_populates="group", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="group", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Group {self.name or self.line_group_id}>"


class GroupApplication(Base):
    """群組申請"""

    __tablename__ = "group_applications"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_group_id: Mapped[str] = mapped_column(String(64), nullable=False)
    group_name: Mapped[Optional[str]] = mapped_column(String(256))
    # 聯絡資訊（申請人姓名、LINE ID 或電話）
    contact_info: Mapped[Optional[str]] = mapped_column(Text)
    # 群組代碼（用於管理員綁定和後台登入，非保密性質）
    group_code: Mapped[Optional[str]] = mapped_column(String(64))

    # 狀態: pending, approved, rejected
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)

    # 審核資訊
    reviewed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    reviewed_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    review_note: Mapped[Optional[str]] = mapped_column(Text)

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯
    reviewer = relationship("User", foreign_keys=[reviewed_by])

    def __repr__(self) -> str:
        return f"<GroupApplication {self.group_name or self.line_group_id}>"


class GroupMember(Base):
    """群組成員"""

    __tablename__ = "group_members"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    joined_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 關聯
    group = relationship("Group", back_populates="members")
    user = relationship("User", back_populates="group_memberships")

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_member"),
    )

    def __repr__(self) -> str:
        return f"<GroupMember group={self.group_id} user={self.user_id}>"


class GroupAdmin(Base):
    """群組管理員"""

    __tablename__ = "group_admins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    granted_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # 關聯
    group = relationship("Group", back_populates="admins")
    user = relationship("User", back_populates="group_admin_roles", foreign_keys=[user_id])
    granter = relationship("User", foreign_keys=[granted_by])

    __table_args__ = (
        UniqueConstraint("group_id", "user_id", name="uq_group_admin"),
    )

    def __repr__(self) -> str:
        return f"<GroupAdmin group={self.group_id} user={self.user_id}>"
