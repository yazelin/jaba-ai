"""廣播模組 - 提供 Socket.IO 廣播功能給其他模組使用

透過依賴注入模式避免循環依賴問題。
main.py 在 lifespan 中註冊廣播函數，其他模組透過 emit_* 函數調用。

重要：所有 emit_* 函數會將事件加入隊列，必須呼叫 flush_events() 或
commit_and_notify(db) 才會實際發送。這確保 Socket 通知在 DB commit 之後。
"""
import logging
from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any, Awaitable, Callable, Dict, List, Optional

from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger("jaba.broadcast")

# 廣播函數類型定義
BroadcastFunc = Callable[[str, dict], Awaitable[None]]


# ===== Event Queue 機制 =====


@dataclass
class PendingEvent:
    """待發送的事件"""
    event_type: str
    room: str
    data: Dict[str, Any]


# Request-scoped event queue (使用 ContextVar 確保每個請求獨立)
_event_queue: ContextVar[List[PendingEvent]] = ContextVar('event_queue')


def _get_queue() -> List[PendingEvent]:
    """取得當前請求的事件隊列"""
    try:
        return _event_queue.get()
    except LookupError:
        queue: List[PendingEvent] = []
        _event_queue.set(queue)
        return queue


def _queue_event(event_type: str, room: str, data: dict) -> None:
    """將事件加入隊列（不立即發送）"""
    queue = _get_queue()
    queue.append(PendingEvent(event_type=event_type, room=room, data=data))
    logger.debug(f"Event queued: {event_type} for room {room}")


# ===== 廣播函數存儲（由 main.py 注入）=====


_broadcast_order_update: Optional[BroadcastFunc] = None
_broadcast_chat_message: Optional[BroadcastFunc] = None
_broadcast_session_status: Optional[BroadcastFunc] = None
_broadcast_payment_update: Optional[BroadcastFunc] = None
_broadcast_store_change: Optional[BroadcastFunc] = None
_broadcast_application_update: Optional[BroadcastFunc] = None
_broadcast_group_update: Optional[BroadcastFunc] = None

# 事件類型到廣播函數的映射
_event_broadcasters: Dict[str, Optional[BroadcastFunc]] = {}


def register_broadcasters(
    order_update: BroadcastFunc,
    chat_message: BroadcastFunc,
    session_status: BroadcastFunc,
    payment_update: BroadcastFunc,
    store_change: BroadcastFunc,
    application_update: BroadcastFunc,
    group_update: BroadcastFunc,
) -> None:
    """由 main.py 調用，注入廣播函數"""
    global _broadcast_order_update, _broadcast_chat_message
    global _broadcast_session_status, _broadcast_payment_update, _broadcast_store_change
    global _broadcast_application_update, _broadcast_group_update
    global _event_broadcasters

    _broadcast_order_update = order_update
    _broadcast_chat_message = chat_message
    _broadcast_session_status = session_status
    _broadcast_payment_update = payment_update
    _broadcast_store_change = store_change
    _broadcast_application_update = application_update
    _broadcast_group_update = group_update

    # 建立映射表供 flush_events 使用
    _event_broadcasters = {
        "order_update": order_update,
        "chat_message": chat_message,
        "session_status": session_status,
        "payment_update": payment_update,
        "store_change": store_change,
        "application_update": application_update,
        "group_update": group_update,
    }

    logger.info("Broadcast functions registered")


# ===== Event Queue 操作函數 =====


async def flush_events() -> None:
    """發送所有隊列中的事件（應在 db.commit() 之後呼叫）"""
    queue = _get_queue()
    if not queue:
        return

    for event in queue:
        broadcaster = _event_broadcasters.get(event.event_type)
        if broadcaster:
            try:
                await broadcaster(event.room, event.data)
                logger.debug(f"Event sent: {event.event_type} to room {event.room}")
            except Exception as e:
                logger.error(f"Failed to broadcast {event.event_type}: {e}")
        else:
            logger.warning(f"No broadcaster registered for event type: {event.event_type}")

    queue.clear()


def clear_events() -> None:
    """清空事件隊列（用於錯誤/rollback 時）"""
    try:
        queue = _event_queue.get()
        queue.clear()
        logger.debug("Event queue cleared")
    except LookupError:
        pass


async def commit_and_notify(db: AsyncSession) -> None:
    """提交資料庫變更並發送所有排隊的事件

    這是推薦的使用方式，確保：
    1. 資料先寫入資料庫
    2. 然後才發送 Socket 通知
    3. 前端收到通知後 fetch 的資料一定是最新的
    """
    await db.commit()
    await flush_events()


# ===== 事件發送函數（加入隊列，不立即發送）=====


async def emit_order_update(group_id: str, data: dict) -> None:
    """將訂單更新事件加入隊列"""
    _queue_event("order_update", group_id, data)


async def emit_chat_message(group_id: str, data: dict) -> None:
    """將聊天訊息事件加入隊列"""
    _queue_event("chat_message", group_id, data)


async def emit_session_status(group_id: str, data: dict) -> None:
    """將 Session 狀態變更事件加入隊列（開單/收單）"""
    _queue_event("session_status", group_id, data)


async def emit_payment_update(group_id: str, data: dict) -> None:
    """將付款狀態變更事件加入隊列"""
    _queue_event("payment_update", group_id, data)


async def emit_store_change(group_id: str, data: dict) -> None:
    """將今日店家變更事件加入隊列"""
    _queue_event("store_change", group_id, data)


async def emit_application_update(data: dict) -> None:
    """將群組申請更新事件加入隊列（廣播給超管後台）"""
    _queue_event("application_update", "admin", data)


async def emit_group_update(data: dict) -> None:
    """將群組更新事件加入隊列（成員變動等）"""
    _queue_event("group_update", "admin", data)
