"""訂單 Repository"""
from datetime import date, datetime
from typing import List, Optional
from uuid import UUID
import zoneinfo

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.order import GroupTodayStore, Order, OrderItem, OrderSession
from app.repositories.base import BaseRepository

# 台北時區
TW_TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def get_today_tw() -> date:
    """取得台北時區的今日日期"""
    return datetime.now(TW_TZ).date()


class GroupTodayStoreRepository(BaseRepository[GroupTodayStore]):
    """群組今日店家 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(GroupTodayStore, session)

    async def get_today_stores(
        self, group_id: UUID, target_date: Optional[date] = None
    ) -> List[GroupTodayStore]:
        """取得群組今日店家"""
        if target_date is None:
            target_date = get_today_tw()

        result = await self.session.execute(
            select(GroupTodayStore)
            .where(
                GroupTodayStore.group_id == group_id,
                GroupTodayStore.date == target_date,
            )
            .options(selectinload(GroupTodayStore.store))
        )
        return list(result.scalars().all())

    async def set_today_store(
        self,
        group_id: UUID,
        store_id: UUID,
        set_by: Optional[UUID] = None,
        target_date: Optional[date] = None,
    ) -> GroupTodayStore:
        """設定群組今日店家"""
        if target_date is None:
            target_date = get_today_tw()

        # 檢查是否已存在
        result = await self.session.execute(
            select(GroupTodayStore).where(
                GroupTodayStore.group_id == group_id,
                GroupTodayStore.store_id == store_id,
                GroupTodayStore.date == target_date,
            )
        )
        today_store = result.scalar_one_or_none()

        if today_store is None:
            today_store = GroupTodayStore(
                group_id=group_id,
                store_id=store_id,
                date=target_date,
                set_by=set_by,
            )
            today_store = await self.create(today_store)

        return today_store

    async def clear_today_stores(
        self, group_id: UUID, target_date: Optional[date] = None
    ) -> None:
        """清除群組今日店家"""
        if target_date is None:
            target_date = get_today_tw()

        result = await self.session.execute(
            select(GroupTodayStore).where(
                GroupTodayStore.group_id == group_id,
                GroupTodayStore.date == target_date,
            )
        )
        for today_store in result.scalars().all():
            await self.session.delete(today_store)
        await self.session.flush()

    async def remove_today_store(
        self, group_id: UUID, store_id: UUID, target_date: Optional[date] = None
    ) -> bool:
        """移除特定今日店家"""
        if target_date is None:
            target_date = get_today_tw()

        result = await self.session.execute(
            select(GroupTodayStore).where(
                GroupTodayStore.group_id == group_id,
                GroupTodayStore.store_id == store_id,
                GroupTodayStore.date == target_date,
            )
        )
        today_store = result.scalar_one_or_none()
        if today_store:
            await self.session.delete(today_store)
            await self.session.flush()
            return True
        return False


class OrderSessionRepository(BaseRepository[OrderSession]):
    """點餐 Session Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(OrderSession, session)

    async def get_active_session(self, group_id: UUID) -> Optional[OrderSession]:
        """取得群組進行中的 Session"""
        result = await self.session.execute(
            select(OrderSession)
            .where(
                OrderSession.group_id == group_id,
                OrderSession.status == "ordering",
            )
            .options(selectinload(OrderSession.orders).selectinload(Order.items))
        )
        return result.scalar_one_or_none()

    async def get_with_orders(self, session_id: UUID) -> Optional[OrderSession]:
        """取得 Session 及其訂單"""
        result = await self.session.execute(
            select(OrderSession)
            .where(OrderSession.id == session_id)
            .options(
                selectinload(OrderSession.orders)
                .selectinload(Order.items),
                selectinload(OrderSession.orders)
                .selectinload(Order.user),
            )
            .execution_options(populate_existing=True)  # 強制從 DB 重新讀取
        )
        return result.scalar_one_or_none()

    async def start_session(
        self, group_id: UUID, started_by: Optional[UUID] = None
    ) -> OrderSession:
        """開始新 Session"""
        session = OrderSession(group_id=group_id, started_by=started_by)
        return await self.create(session)

    async def end_session(
        self, session: OrderSession, ended_by: Optional[UUID] = None
    ) -> OrderSession:
        """結束 Session"""
        session.status = "ended"
        session.ended_at = datetime.now()
        session.ended_by = ended_by
        return await self.update(session)

    async def get_group_sessions(
        self,
        group_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> List[OrderSession]:
        """取得群組的 Session 歷史"""
        from datetime import datetime, timedelta
        import zoneinfo

        query = select(OrderSession).where(OrderSession.group_id == group_id)

        # 使用本地時區的日期範圍轉換為 UTC datetime 進行比較
        local_tz = zoneinfo.ZoneInfo("Asia/Taipei")
        if start_date:
            # 將本地日期開始轉換為 UTC
            start_dt = datetime.combine(start_date, datetime.min.time()).replace(tzinfo=local_tz)
            query = query.where(OrderSession.created_at >= start_dt)
        if end_date:
            # 將本地日期結束（隔天凌晨）轉換為 UTC
            end_dt = datetime.combine(end_date + timedelta(days=1), datetime.min.time()).replace(tzinfo=local_tz)
            query = query.where(OrderSession.created_at < end_dt)

        query = query.order_by(OrderSession.created_at.desc())

        result = await self.session.execute(query)
        return list(result.scalars().all())


class OrderRepository(BaseRepository[Order]):
    """訂單 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(Order, session)

    async def get_by_session_and_user(
        self, session_id: UUID, user_id: UUID
    ) -> Optional[Order]:
        """取得使用者在 Session 中的訂單"""
        result = await self.session.execute(
            select(Order)
            .where(Order.session_id == session_id, Order.user_id == user_id)
            .options(selectinload(Order.items))
        )
        return result.scalar_one_or_none()

    async def get_session_orders(self, session_id: UUID) -> List[Order]:
        """取得 Session 的所有訂單"""
        result = await self.session.execute(
            select(Order)
            .where(Order.session_id == session_id)
            .options(
                selectinload(Order.items),
                selectinload(Order.user),
            )
        )
        return list(result.scalars().all())

    async def calculate_total(self, order: Order) -> Order:
        """計算訂單總金額"""
        # 直接從資料庫計算品項總額，避免 SQLAlchemy identity map 快取問題
        # 這確保新增的品項會被正確計入總金額
        result = await self.session.execute(
            select(func.coalesce(func.sum(OrderItem.subtotal), 0))
            .where(OrderItem.order_id == order.id)
        )
        total = result.scalar()
        order.total_amount = total
        return await self.update(order)


class OrderItemRepository(BaseRepository[OrderItem]):
    """訂單品項 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(OrderItem, session)
