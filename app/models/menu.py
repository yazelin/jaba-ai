"""菜單相關模型"""
import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models import Base


class Menu(Base):
    """菜單"""

    __tablename__ = "menus"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    store_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("stores.id", ondelete="CASCADE"), index=True
    )

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯
    store = relationship("Store", back_populates="menu")
    categories = relationship(
        "MenuCategory", back_populates="menu", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Menu store={self.store_id}>"


class MenuCategory(Base):
    """菜單分類"""

    __tablename__ = "menu_categories"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    menu_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menus.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯
    menu = relationship("Menu", back_populates="categories")
    items = relationship(
        "MenuItem", back_populates="category", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<MenuCategory {self.name}>"


class MenuItem(Base):
    """菜單品項"""

    __tablename__ = "menu_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("menu_categories.id", ondelete="CASCADE"), index=True
    )
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    price: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text)

    is_available: Mapped[bool] = mapped_column(Boolean, default=True, index=True)

    # 尺寸變體 (JSONB): [{"name": "M", "price": 35}, {"name": "L", "price": 40}]
    variants: Mapped[list] = mapped_column(JSONB, default=list)

    # 促銷資訊 (JSONB): {"type": "discount", "label": "買一送一", "value": 50}
    promo: Mapped[Optional[dict]] = mapped_column(JSONB)

    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # 時間戳記
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # 關聯
    category = relationship("MenuCategory", back_populates="items")
    order_items = relationship("OrderItem", back_populates="menu_item")

    def __repr__(self) -> str:
        return f"<MenuItem {self.name} ${self.price}>"
