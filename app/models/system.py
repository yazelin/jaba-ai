"""系統設定模型"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class SuperAdmin(Base):
    """超級管理員"""

    __tablename__ = "super_admins"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<SuperAdmin {self.username}>"


class AiPrompt(Base):
    """AI 提示詞"""

    __tablename__ = "ai_prompts"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    def __repr__(self) -> str:
        return f"<AiPrompt {self.name}>"


class SecurityLog(Base):
    """安全日誌 - 記錄可疑輸入"""

    __tablename__ = "security_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    line_user_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    display_name: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    line_group_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
    original_message: Mapped[str] = mapped_column(Text, nullable=False)
    sanitized_message: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_reasons: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    context_type: Mapped[str] = mapped_column(String(16), nullable=False)  # group/personal

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    def __repr__(self) -> str:
        return f"<SecurityLog {self.line_user_id} {self.created_at}>"
