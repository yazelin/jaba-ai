"""使用者 Repository"""
from datetime import datetime
from typing import Optional, List, Tuple
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.user import User
from app.models.group import GroupMember
from app.models.order import Order
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """使用者 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(User, session)

    async def get_by_line_user_id(self, line_user_id: str) -> Optional[User]:
        """根據 LINE User ID 取得使用者"""
        result = await self.session.execute(
            select(User).where(User.line_user_id == line_user_id)
        )
        return result.scalar_one_or_none()

    async def get_or_create(
        self, line_user_id: str, display_name: Optional[str] = None
    ) -> User:
        """取得或建立使用者"""
        user = await self.get_by_line_user_id(line_user_id)
        if user is None:
            user = User(line_user_id=line_user_id, display_name=display_name)
            user = await self.create(user)
        elif display_name and user.display_name != display_name:
            user.display_name = display_name
            user = await self.update(user)
        return user

    async def get_all_paginated(
        self,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[User], int]:
        """分頁取得使用者列表

        Args:
            limit: 每頁數量
            offset: 偏移量
            search: 搜尋關鍵字（名稱或 LINE ID）
            status: 狀態篩選（all/active/banned）

        Returns:
            (使用者列表, 總數)
        """
        query = select(User)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    User.display_name.ilike(search_pattern),
                    User.line_user_id.ilike(search_pattern),
                )
            )

        # 狀態篩選
        if status == "banned":
            query = query.where(User.is_banned == True)
        elif status == "active":
            query = query.where(User.is_banned == False)

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 取得分頁資料
        query = query.order_by(User.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        users = list(result.scalars().all())

        return users, total

    async def get_user_with_stats(self, user_id: UUID) -> Optional[dict]:
        """取得使用者詳情含統計資訊"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        # 取得群組數
        group_count_result = await self.session.execute(
            select(func.count(GroupMember.id)).where(GroupMember.user_id == user_id)
        )
        group_count = group_count_result.scalar() or 0

        # 取得訂單數
        order_count_result = await self.session.execute(
            select(func.count(Order.id)).where(Order.user_id == user_id)
        )
        order_count = order_count_result.scalar() or 0

        return {
            "user": user,
            "group_count": group_count,
            "order_count": order_count,
        }

    async def get_user_groups(self, user_id: UUID) -> List[dict]:
        """取得使用者所屬群組"""
        from app.models.group import Group

        result = await self.session.execute(
            select(Group)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user_id)
        )
        groups = result.scalars().all()

        return [
            {
                "id": str(g.id),
                "name": g.name,
                "line_group_id": g.line_group_id,
                "status": g.status,
            }
            for g in groups
        ]

    async def get_user_recent_orders(
        self, user_id: UUID, limit: int = 10
    ) -> List[dict]:
        """取得使用者最近訂單"""
        from app.models.order import OrderItem

        result = await self.session.execute(
            select(Order)
            .options(selectinload(Order.items))
            .where(Order.user_id == user_id)
            .order_by(Order.created_at.desc())
            .limit(limit)
        )
        orders = result.scalars().all()

        return [
            {
                "id": str(o.id),
                "total_amount": float(o.total_amount),
                "payment_status": o.payment_status,
                "created_at": o.created_at.isoformat(),
                "items": [
                    {"name": item.name, "quantity": item.quantity}
                    for item in o.items
                ],
            }
            for o in orders
        ]

    async def ban_user(self, user_id: UUID) -> Optional[User]:
        """封鎖使用者"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_banned = True
        user.banned_at = datetime.utcnow()
        await self.session.flush()
        return user

    async def unban_user(self, user_id: UUID) -> Optional[User]:
        """解除封鎖"""
        user = await self.get_by_id(user_id)
        if not user:
            return None

        user.is_banned = False
        user.banned_at = None
        await self.session.flush()
        return user
