"""店家模型"""
import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, String, Text, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Store(Base):
    """店家"""

    __tablename__ = "stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String(100))
    address: Mapped[Optional[str]] = mapped_column(Text)
    description: Mapped[Optional[str]] = mapped_column(Text)
    note: Mapped[Optional[str]] = mapped_column(Text)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # 店家層級：global（全局）或 group（群組專屬）
    scope: Mapped[str] = mapped_column(String(16), default="global", index=True)
    # 群組代碼（scope=group 時使用）
    group_code: Mapped[Optional[str]] = mapped_column(String(64), index=True)
    # 建立者類型：admin（超管）或 line_admin（LINE 管理員）
    created_by_type: Mapped[str] = mapped_column(String(16), default="admin")

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯（cascade 確保刪除店家時連帶刪除相關資料）
    menu = relationship("Menu", back_populates="store", uselist=False, cascade="all, delete-orphan")
    today_stores = relationship("GroupTodayStore", back_populates="store", cascade="all, delete-orphan")
    orders = relationship("Order", back_populates="store", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Store {self.name}>"
