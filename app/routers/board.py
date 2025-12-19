"""看板 API 路由"""
from datetime import date
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories import (
    GroupRepository,
    OrderSessionRepository,
    ChatRepository,
    GroupTodayStoreRepository,
)

router = APIRouter(prefix="/api/board", tags=["board"])


@router.get("/groups")
async def get_groups(
    db: AsyncSession = Depends(get_db),
):
    """取得所有已啟用群組"""
    repo = GroupRepository(db)
    groups = await repo.get_active_groups()

    return [
        {
            "id": str(group.id),
            "line_group_id": group.line_group_id,
            "name": group.name,
        }
        for group in groups
    ]


@router.get("/orders")
async def get_board_orders(
    group_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """取得看板訂單（當日）"""
    session_repo = OrderSessionRepository(db)
    group_repo = GroupRepository(db)

    result = []

    if group_id:
        # 指定群組
        groups = [await group_repo.get_by_id(group_id)]
    else:
        # 所有已啟用群組
        groups = await group_repo.get_active_groups()

    for group in groups:
        if not group:
            continue

        # 取得今日的 Session
        sessions = await session_repo.get_group_sessions(
            group.id, start_date=date.today(), end_date=date.today()
        )

        for session in sessions:
            session_with_orders = await session_repo.get_with_orders(session.id)
            if not session_with_orders:
                continue

            orders = []
            for order in session_with_orders.orders:
                orders.append({
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
                })

            result.append({
                "group_id": str(group.id),
                "group_name": group.name,
                "session_id": str(session.id),
                "session_status": session.status,
                "orders": orders,
                "total": sum(o["total"] for o in orders),
                "count": len(orders),
            })

    return result


@router.get("/chat")
async def get_board_chat(
    group_id: Optional[UUID] = None,
    limit: int = Query(50, le=100),
    db: AsyncSession = Depends(get_db),
):
    """取得看板聊天訊息（當日）"""
    repo = ChatRepository(db)
    messages = await repo.get_today_messages(group_id, limit)

    return [
        {
            "id": str(msg.id),
            "group_id": str(msg.group_id) if msg.group_id else None,
            "user_id": str(msg.user_id) if msg.user_id else None,
            "display_name": msg.user.display_name if msg.user else "系統",
            "role": msg.role,
            "content": msg.content,
            "created_at": msg.created_at.isoformat(),
        }
        for msg in messages
    ]


@router.get("/today-stores")
async def get_all_today_stores(
    group_id: Optional[UUID] = None,
    db: AsyncSession = Depends(get_db),
):
    """取得所有群組的今日店家"""
    today_repo = GroupTodayStoreRepository(db)
    group_repo = GroupRepository(db)

    result = []

    if group_id:
        groups = [await group_repo.get_by_id(group_id)]
    else:
        groups = await group_repo.get_active_groups()

    for group in groups:
        if not group:
            continue

        today_stores = await today_repo.get_today_stores(group.id)
        result.append({
            "group_id": str(group.id),
            "group_name": group.name,
            "stores": [
                {
                    "store_id": str(ts.store_id),
                    "store_name": ts.store.name if ts.store else None,
                }
                for ts in today_stores
            ],
        })

    return result
