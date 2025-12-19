# Change: 新增即時廣播整合與管理員代理點餐功能

## Why

新版 jaba-ai 雖然已定義 Socket.IO 廣播函數（`broadcast_order_update`、`broadcast_chat_message`），但這些函數未在實際的訂單操作和聊天訊息處理中被調用，導致：

1. **看板無法即時更新**：使用者需要手動刷新頁面才能看到新訂單
2. **聊天區無法即時顯示**：看板的「美食評論區」無法即時顯示新訊息
3. **管理員無法代理點餐**：舊版支援的代理點餐功能在新版中缺失

這些是從舊版 jaba 遷移時遺漏的功能完善工作。

## What Changes

### 1. Socket.IO 即時廣播整合
- 在 `LineService` 的訂單操作後調用 `broadcast_order_update()`
- 在聊天訊息處理後調用 `broadcast_chat_message()`
- 新增 `broadcast_session_status()` 廣播開單/收單狀態
- 新增 `broadcast_payment_update()` 廣播付款狀態變更
- 新增 `broadcast_store_change()` 廣播今日店家變更

### 2. 超級管理員代理點餐 API
- `POST /api/admin/groups/{group_id}/orders` - 代理建立訂單
- `PUT /api/admin/groups/{group_id}/orders/{order_id}` - 代理修改訂單

### 3. 清除群組訂單功能
- `DELETE /api/admin/sessions/{session_id}/orders` - 清除 Session 所有訂單

## Impact

- **Affected specs**: realtime-broadcast (新增), admin-proxy-order (新增)
- **Affected code**:
  - `main.py` - 新增廣播函數
  - `app/services/line_service.py` - 調用廣播函數
  - `app/services/order_service.py` - 調用廣播函數
  - `app/routers/admin.py` - 新增代理點餐 API
