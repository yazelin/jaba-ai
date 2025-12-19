"""訂單相關模型"""
import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Date, DateTime, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class GroupTodayStore(Base):
    """群組今日店家"""

    __tablename__ = "group_today_stores"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE")
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE")
    )
    date: Mapped[date] = mapped_column(Date, default=date.today)

    set_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    set_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 關聯
    group = relationship("Group", back_populates="today_stores")
    store = relationship("Store", back_populates="today_stores")
    setter = relationship("User", foreign_keys=[set_by])

    __table_args__ = (
        UniqueConstraint("group_id", "store_id", "date", name="uq_group_today_store"),
    )

    def __repr__(self) -> str:
        return f"<GroupTodayStore group={self.group_id} store={self.store_id} date={self.date}>"


class OrderSession(Base):
    """點餐 Session"""

    __tablename__ = "order_sessions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    group_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("groups.id", ondelete="CASCADE"), index=True
    )

    # 狀態: ordering, ended
    status: Mapped[str] = mapped_column(String(32), default="ordering", index=True)

    # 開始/結束資訊
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    started_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )
    ended_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    ended_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id")
    )

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯
    group = relationship("Group", back_populates="order_sessions")
    starter = relationship("User", foreign_keys=[started_by])
    ender = relationship("User", foreign_keys=[ended_by])
    orders = relationship("Order", back_populates="session", cascade="all, delete-orphan")
    chat_messages = relationship("ChatMessage", back_populates="session")

    def __repr__(self) -> str:
        return f"<OrderSession {self.id} status={self.status}>"


class Order(Base):
    """訂單"""

    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("order_sessions.id", ondelete="CASCADE"), index=True
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id")
    )

    total_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)

    # 付款狀態: unpaid, paid, refunded
    payment_status: Mapped[str] = mapped_column(String(32), default="unpaid")
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=0)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯
    session = relationship("OrderSession", back_populates="orders")
    user = relationship("User", back_populates="orders")
    store = relationship("Store", back_populates="orders")
    items = relationship("OrderItem", back_populates="order", cascade="all, delete-orphan")

    def __repr__(self) -> str:
        return f"<Order {self.id} total=${self.total_amount}>"


class OrderItem(Base):
    """訂單品項"""

    __tablename__ = "order_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("orders.id", ondelete="CASCADE"), index=True
    )
    menu_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_items.id")
    )

    name: Mapped[str] = mapped_column(String(256), nullable=False)
    quantity: Mapped[int] = mapped_column(Integer, default=1)
    unit_price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    subtotal: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)

    # 客製化選項 (JSONB): {"size": "L", "sugar": "微糖", "ice": "去冰"}
    options: Mapped[dict] = mapped_column(JSONB, default=dict)

    note: Mapped[Optional[str]] = mapped_column(Text)

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    # 關聯
    order = relationship("Order", back_populates="items")
    menu_item = relationship("MenuItem", back_populates="order_items")

    def __repr__(self) -> str:
        return f"<OrderItem {self.name} x{self.quantity}>"
