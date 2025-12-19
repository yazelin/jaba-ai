# Design: 即時廣播整合與管理員代理點餐

## Context

新版 jaba-ai 已經有 Socket.IO 基礎設施（`main.py` 中的 `sio` 實例），並定義了兩個廣播函數：
- `broadcast_order_update(group_id, data)` - 訂單更新廣播
- `broadcast_chat_message(group_id, data)` - 聊天訊息廣播

問題是這些函數從未被調用，導致前端無法即時更新。

## Goals / Non-Goals

### Goals
- 實現看板和管理員頁面的即時更新
- 恢復舊版的管理員代理點餐功能
- 最小化程式碼變更，利用現有基礎設施

### Non-Goals
- 不重構 Socket.IO 架構
- 不新增 WebSocket 認證機制（沿用現有的 room 機制）
- 不處理離線訊息佇列

## Decisions

### 1. 廣播觸發點

在以下位置調用廣播函數：

| 事件 | 觸發位置 | 廣播函數 |
|------|----------|----------|
| 訂單變更 | `LineService._action_create_order` 等 | `broadcast_order_update` |
| 聊天訊息 | `LineService._handle_group_message` | `broadcast_chat_message` |
| 開單/收單 | `LineService._start_ordering/_end_ordering` | `broadcast_session_status` |
| 付款狀態 | `OrderService.mark_paid/refund` | `broadcast_payment_update` |
| 今日店家 | `admin.py` 設定今日店家 API | `broadcast_store_change` |

### 2. 廣播函數設計

新增函數於 `main.py`：

```python
async def broadcast_session_status(group_id: str, data: dict):
    """廣播 Session 狀態變更（開單/收單）"""
    await sio.emit("session_status", data, room=f"board:{group_id}")
    await sio.emit("session_status", data, room="board:all")

async def broadcast_payment_update(group_id: str, data: dict):
    """廣播付款狀態變更"""
    await sio.emit("payment_update", data, room=f"board:{group_id}")
    await sio.emit("payment_update", data, room="board:all")

async def broadcast_store_change(group_id: str, data: dict):
    """廣播今日店家變更"""
    await sio.emit("store_change", data, room=f"board:{group_id}")
    await sio.emit("store_change", data, room="board:all")
```

### 3. 跨模組調用方案

由於 `LineService` 和 `OrderService` 在 `app/services/` 目錄，無法直接 import `main.py` 的函數（會造成循環依賴），採用以下方案：

**方案：建立 `app/broadcast.py` 模組**

```python
# app/broadcast.py
from typing import Optional, Callable, Awaitable

# 廣播函數存儲（由 main.py 注入）
_broadcast_order_update: Optional[Callable] = None
_broadcast_chat_message: Optional[Callable] = None
_broadcast_session_status: Optional[Callable] = None
_broadcast_payment_update: Optional[Callable] = None
_broadcast_store_change: Optional[Callable] = None

def register_broadcasters(
    order_update: Callable,
    chat_message: Callable,
    session_status: Callable,
    payment_update: Callable,
    store_change: Callable,
):
    """由 main.py 調用，注入廣播函數"""
    global _broadcast_order_update, _broadcast_chat_message
    global _broadcast_session_status, _broadcast_payment_update, _broadcast_store_change
    _broadcast_order_update = order_update
    _broadcast_chat_message = chat_message
    _broadcast_session_status = session_status
    _broadcast_payment_update = payment_update
    _broadcast_store_change = store_change

async def emit_order_update(group_id: str, data: dict):
    if _broadcast_order_update:
        await _broadcast_order_update(group_id, data)

async def emit_chat_message(group_id: str, data: dict):
    if _broadcast_chat_message:
        await _broadcast_chat_message(group_id, data)

async def emit_session_status(group_id: str, data: dict):
    if _broadcast_session_status:
        await _broadcast_session_status(group_id, data)

async def emit_payment_update(group_id: str, data: dict):
    if _broadcast_payment_update:
        await _broadcast_payment_update(group_id, data)

async def emit_store_change(group_id: str, data: dict):
    if _broadcast_store_change:
        await _broadcast_store_change(group_id, data)
```

在 `main.py` 的 `lifespan` 中註冊：

```python
from app.broadcast import register_broadcasters

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 註冊廣播函數
    register_broadcasters(
        order_update=broadcast_order_update,
        chat_message=broadcast_chat_message,
        session_status=broadcast_session_status,
        payment_update=broadcast_payment_update,
        store_change=broadcast_store_change,
    )
    ...
```

### 4. 代理點餐 API 設計

```
POST /api/admin/groups/{group_id}/proxy-orders
Request:
{
  "user_id": "uuid",           # 目標使用者 ID
  "items": [
    {"name": "排骨便當", "quantity": 1, "note": "不要酸菜"}
  ]
}
Response:
{
  "success": true,
  "order_id": "uuid"
}

PUT /api/admin/groups/{group_id}/proxy-orders/{order_id}
Request:
{
  "items": [
    {"name": "雞腿便當", "quantity": 2}
  ]
}
Response:
{
  "success": true
}

DELETE /api/admin/sessions/{session_id}/orders
Response:
{
  "success": true,
  "deleted_count": 5
}
```

## Risks / Trade-offs

| 風險 | 緩解措施 |
|------|----------|
| 廣播失敗不影響主要業務 | 廣播調用使用 try-except 包裝，失敗只記錄 log |
| 循環依賴 | 使用依賴注入模式（broadcast.py）|
| 前端未處理新事件 | 前端需同步更新監聽事件 |

## Open Questions

1. 是否需要限制廣播頻率（debounce）？
   - 決定：暫不實作，觀察實際使用情況

2. 是否需要訊息持久化（離線客戶端重連後補發）？
   - 決定：暫不實作，前端重連時會重新載入資料
