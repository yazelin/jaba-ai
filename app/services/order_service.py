"""訂單服務"""
import logging
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.models.order import Order, OrderItem, OrderSession
from app.repositories import (
    OrderRepository,
    OrderItemRepository,
    OrderSessionRepository,
    GroupTodayStoreRepository,
)
from app.services.cache_service import CacheService

logger = logging.getLogger("jaba.order")


class OrderService:
    """訂單服務"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.order_repo = OrderRepository(session)
        self.order_item_repo = OrderItemRepository(session)
        self.session_repo = OrderSessionRepository(session)
        self.today_store_repo = GroupTodayStoreRepository(session)

    async def start_ordering(
        self, group_id: UUID, started_by: Optional[UUID] = None
    ) -> OrderSession:
        """開始點餐 Session"""
        # 檢查是否已有進行中的 Session
        active_session = await self.session_repo.get_active_session(group_id)
        if active_session:
            return active_session

        # 建立新 Session
        return await self.session_repo.start_session(group_id, started_by)

    async def end_ordering(
        self, group_id: UUID, ended_by: Optional[UUID] = None
    ) -> Optional[OrderSession]:
        """結束點餐 Session"""
        active_session = await self.session_repo.get_active_session(group_id)
        if not active_session:
            return None

        return await self.session_repo.end_session(active_session, ended_by)

    async def get_active_session(self, group_id: UUID) -> Optional[OrderSession]:
        """取得進行中的 Session"""
        return await self.session_repo.get_active_session(group_id)

    async def create_order(
        self,
        session_id: UUID,
        user_id: UUID,
        store_id: UUID,
        items: List[dict],
    ) -> Order:
        """
        建立訂單

        items: [
            {
                "name": "品項名稱",
                "quantity": 1,
                "unit_price": 100,
                "options": {"size": "L", "sugar": "微糖"},
                "note": "備註",
                "menu_item_id": Optional[UUID]
            }
        ]
        """
        # 檢查是否已有訂單
        existing_order = await self.order_repo.get_by_session_and_user(
            session_id, user_id
        )

        if existing_order:
            # 更新現有訂單
            order = existing_order
        else:
            # 建立新訂單
            order = Order(
                session_id=session_id,
                user_id=user_id,
                store_id=store_id,
            )
            order = await self.order_repo.create(order)

        # 新增品項
        for item_data in items:
            quantity = item_data.get("quantity", 1)
            unit_price = Decimal(str(item_data["unit_price"]))
            subtotal = unit_price * quantity

            item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data.get("menu_item_id"),
                name=item_data["name"],
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                options=item_data.get("options", {}),
                note=item_data.get("note"),
            )
            await self.order_item_repo.create(item)

        # 重新計算總金額
        await self.session.refresh(order, ["items"])
        order = await self.order_repo.calculate_total(order)

        return order

    async def update_order(
        self,
        order_id: UUID,
        items: List[dict],
    ) -> Order:
        """更新訂單品項"""
        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        # 刪除現有品項
        for item in order.items:
            await self.order_item_repo.delete(item)

        # 新增新品項
        for item_data in items:
            quantity = item_data.get("quantity", 1)
            unit_price = Decimal(str(item_data["unit_price"]))
            subtotal = unit_price * quantity

            item = OrderItem(
                order_id=order.id,
                menu_item_id=item_data.get("menu_item_id"),
                name=item_data["name"],
                quantity=quantity,
                unit_price=unit_price,
                subtotal=subtotal,
                options=item_data.get("options", {}),
                note=item_data.get("note"),
            )
            await self.order_item_repo.create(item)

        # 重新計算總金額
        await self.session.refresh(order, ["items"])
        order = await self.order_repo.calculate_total(order)

        return order

    async def cancel_order(self, order_id: UUID) -> None:
        """取消訂單"""
        order = await self.order_repo.get_by_id(order_id)
        if order:
            await self.order_repo.delete(order)

    async def get_session_summary(self, session_id: UUID) -> dict:
        """取得 Session 訂單摘要"""
        session = await self.session_repo.get_with_orders(session_id)
        if not session:
            return {"orders": [], "total": 0, "count": 0}

        orders = []
        total = Decimal(0)

        for order in session.orders:
            order_data = {
                "user_id": str(order.user_id),
                "display_name": order.user.display_name if order.user else "未知",
                "items": [
                    {
                        "name": item.name,
                        "quantity": item.quantity,
                        "subtotal": float(item.subtotal),
                        "options": item.options,
                        "note": item.note,
                    }
                    for item in order.items
                ],
                "total": float(order.total_amount),
                "payment_status": order.payment_status,
            }
            orders.append(order_data)
            total += order.total_amount

        return {
            "orders": orders,
            "total": float(total),
            "count": len(orders),
        }

    async def mark_paid(
        self,
        order_id: UUID,
        paid_amount: Optional[Decimal] = None,
    ) -> Order:
        """標記訂單已付款"""
        from app.broadcast import emit_payment_update

        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order.payment_status = "paid"
        order.paid_amount = paid_amount or order.total_amount
        from datetime import datetime
        order.paid_at = datetime.now()

        order = await self.order_repo.update(order)

        # 取得 group_id 並廣播付款狀態
        session = await self.session_repo.get_by_id(order.session_id)
        if session:
            await emit_payment_update(str(session.group_id), {
                "group_id": str(session.group_id),
                "order_id": str(order.id),
                "user_id": str(order.user_id),
                "payment_status": "paid",
                "paid_amount": float(order.paid_amount),
            })

        return order

    async def refund(self, order_id: UUID) -> Order:
        """退款"""
        from app.broadcast import emit_payment_update

        order = await self.order_repo.get_by_id(order_id)
        if not order:
            raise ValueError(f"Order {order_id} not found")

        order.payment_status = "refunded"
        order = await self.order_repo.update(order)

        # 取得 group_id 並廣播付款狀態
        session = await self.session_repo.get_by_id(order.session_id)
        if session:
            await emit_payment_update(str(session.group_id), {
                "group_id": str(session.group_id),
                "order_id": str(order.id),
                "user_id": str(order.user_id),
                "payment_status": "refunded",
            })

        return order

    async def clear_session_orders(self, session_id: UUID) -> int:
        """清除 Session 所有訂單"""
        from app.broadcast import emit_order_update

        session = await self.session_repo.get_with_orders(session_id)
        if not session:
            raise ValueError(f"Session {session_id} not found")

        deleted_count = len(session.orders)

        # 刪除所有訂單（包含品項會因 cascade 自動刪除）
        for order in session.orders:
            await self.order_repo.delete(order)

        # 廣播訂單清除
        await emit_order_update(str(session.group_id), {
            "group_id": str(session.group_id),
            "session_id": str(session_id),
            "action": "cleared",
            "deleted_count": deleted_count,
        })

        return deleted_count
