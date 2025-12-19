from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """SQLAlchemy Base class"""
    pass


# 匯出所有 models
from app.models.user import User
from app.models.group import Group, GroupApplication, GroupMember, GroupAdmin
from app.models.store import Store
from app.models.menu import Menu, MenuCategory, MenuItem
from app.models.order import GroupTodayStore, OrderSession, Order, OrderItem
from app.models.chat import ChatMessage
from app.models.system import SuperAdmin, AiPrompt

__all__ = [
    "Base",
    "User",
    "Group",
    "GroupApplication",
    "GroupMember",
    "GroupAdmin",
    "Store",
    "Menu",
    "MenuCategory",
    "MenuItem",
    "GroupTodayStore",
    "OrderSession",
    "Order",
    "OrderItem",
    "ChatMessage",
    "SuperAdmin",
    "AiPrompt",
]
