# Design: fix-broadcast-race-condition

## Architecture Overview

### 問題分析

```
目前流程（有 Race Condition）:
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Service │───▶│  Emit   │───▶│ Router  │───▶│ Commit  │
│ Update  │    │ Socket  │    │ Return  │    │   DB    │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                   │
                   ▼
              ┌─────────┐
              │ Frontend│──────▶ Fetch 舊資料！
              │ Receive │
              └─────────┘
```

```
修正後流程:
┌─────────┐    ┌─────────┐    ┌─────────┐    ┌─────────┐
│ Service │───▶│  Queue  │───▶│ Commit  │───▶│  Flush  │
│ Update  │    │  Event  │    │   DB    │    │ Events  │
└─────────┘    └─────────┘    └─────────┘    └─────────┘
                                                  │
                                                  ▼
                                             ┌─────────┐
                                             │ Frontend│──▶ Fetch 新資料 ✓
                                             │ Receive │
                                             └─────────┘
```

### 技術方案

#### 1. Event Queue (使用 ContextVar)

```python
from contextvars import ContextVar

# Request-scoped event queue
_event_queue: ContextVar[List[PendingEvent]] = ContextVar('event_queue')
```

**為什麼用 ContextVar?**
- Python 標準庫，專門設計給 async/await 的 request-scoped 狀態
- 每個 async task（HTTP request）有自己的隊列
- 不需要顯式傳遞參數
- 不需要 middleware 初始化

#### 2. 核心 API

```python
# broadcast.py 新增

@dataclass
class PendingEvent:
    event_type: str  # "order_update", "payment_update", etc.
    room: str        # group_id or "all"
    data: dict

def _queue_event(event_type: str, room: str, data: dict) -> None:
    """將事件加入隊列（不立即發送）"""
    queue = _get_queue()
    queue.append(PendingEvent(event_type, room, data))

async def flush_events() -> None:
    """發送所有隊列中的事件（在 db.commit() 之後呼叫）"""
    queue = _get_queue()
    for event in queue:
        await _event_broadcasters[event.event_type](event.room, event.data)
    queue.clear()

def clear_events() -> None:
    """清空事件隊列（用於錯誤/rollback 時）"""
    _get_queue().clear()

async def commit_and_notify(db: AsyncSession) -> None:
    """提交資料庫變更並發送所有排隊的事件"""
    await db.commit()
    await flush_events()
```

#### 3. emit_* 函數改為 Queue

```python
# 改變前
async def emit_order_update(group_id: str, data: dict) -> None:
    if _broadcast_order_update:
        await _broadcast_order_update(group_id, data)

# 改變後
async def emit_order_update(group_id: str, data: dict) -> None:
    _queue_event("order_update", group_id, data)
```

**注意**：emit_* 函數保持 async 簽名以維持向後相容，但實際上不再是 async 操作。

#### 4. Router 使用方式

```python
# 改變前
@router.post("/orders/{order_id}/mark-paid")
async def mark_order_paid(order_id: UUID, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    await service.mark_paid(order_id)  # 這裡面會 emit
    await db.commit()
    return {"success": True}

# 改變後
from app.broadcast import commit_and_notify

@router.post("/orders/{order_id}/mark-paid")
async def mark_order_paid(order_id: UUID, db: AsyncSession = Depends(get_db)):
    service = OrderService(db)
    await service.mark_paid(order_id)  # emit 變成 queue event
    await commit_and_notify(db)        # commit + flush events
    return {"success": True}
```

### 錯誤處理

```python
@router.post("/some-endpoint")
async def some_endpoint(db: AsyncSession = Depends(get_db)):
    try:
        await service.do_something()  # 可能會 queue events
        await commit_and_notify(db)
    except Exception:
        clear_events()  # 確保失敗時不會發送事件
        raise
```

### 邊界情況

#### LINE Webhook 處理
LINE Webhook 的處理在 `line_service.py` 中，有自己的 session 管理。
這些流程會直接在 service 內 commit，不經過 router 的 `commit_and_notify`。

**解法**：在 line_service 的相關方法結尾加上 `await flush_events()`

#### 無 emit 的 commit
某些 endpoint 只有 commit 沒有 emit，這些可以：
1. 繼續使用 `await db.commit()`（`flush_events` 在空隊列時是 no-op）
2. 或統一改用 `await commit_and_notify(db)` 以維持一致性

建議統一使用 `commit_and_notify` 以簡化程式碼審查。

### 測試策略

1. **單元測試**：驗證 `_queue_event` 和 `flush_events` 的行為
2. **整合測試**：模擬 race condition 場景，確認修正後行為正確
3. **手動測試**：在前端操作確認收款、設定今日店家等功能的即時更新
