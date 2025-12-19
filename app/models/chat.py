"""對話記錄模型"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class ChatMessage(Base):
    """對話記錄"""

    __tablename__ = "chat_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 可以是群組對話或個人對話
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE")
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # 角色: user, assistant
    role: Mapped[str] = mapped_column(String(32), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 關聯的 session (如果是點餐對話)
    session_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_sessions.id", ondelete="SET NULL")
    )

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # 關聯
    group = relationship("Group", back_populates="chat_messages")
    user = relationship("User", back_populates="chat_messages")
    session = relationship("OrderSession", back_populates="chat_messages")

    __table_args__ = (
        # 複合索引用於查詢群組對話
        # Index("idx_chat_messages_group_created", "group_id", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<ChatMessage {self.role}: {self.content[:30]}...>"
