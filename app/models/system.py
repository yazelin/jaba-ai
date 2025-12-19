"""系統設定模型"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

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


class AiLog(Base):
    """AI 對話日誌 - 記錄 AI 輸入與輸出供分析"""

    __tablename__ = "ai_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # 關聯（可為空，因為可能是個人對話或系統對話）
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True
    )
    group_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="SET NULL"), nullable=True, index=True
    )

    # AI 模型資訊
    model: Mapped[str] = mapped_column(String(32), nullable=False)  # haiku, opus, etc.

    # 輸入：完整的 prompt context
    input_prompt: Mapped[str] = mapped_column(Text, nullable=False)

    # 輸出：AI 原始回應（包含思考過程）
    raw_response: Mapped[str] = mapped_column(Text, nullable=False)

    # 解析結果
    parsed_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    parsed_actions: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # 執行狀態
    success: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    duration_ms: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Token 統計（簡易估算）
    input_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    output_tokens: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    # 關聯
    user = relationship("User", foreign_keys=[user_id])
    group = relationship("Group", foreign_keys=[group_id])

    def __repr__(self) -> str:
        return f"<AiLog {self.id} {self.created_at}>"
