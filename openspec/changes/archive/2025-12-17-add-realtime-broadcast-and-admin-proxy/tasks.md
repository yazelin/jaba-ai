# Implementation Tasks

## 1. 廣播模組基礎建設

- [x] 1.1 建立 `app/broadcast.py` 模組
  - 定義廣播函數存儲變數
  - 實作 `register_broadcasters()` 註冊函數
  - 實作 `emit_order_update()` 等封裝函數
- [x] 1.2 在 `main.py` 新增廣播函數
  - `broadcast_session_status()`
  - `broadcast_payment_update()`
  - `broadcast_store_change()`
- [x] 1.3 在 `main.py` lifespan 中註冊廣播函數
  - 調用 `register_broadcasters()` 注入所有廣播函數
- **驗證**: 啟動應用，確認無 import 錯誤

## 2. 訂單變更廣播整合

- [x] 2.1 在 `LineService._action_create_order` 調用 `emit_order_update()`
- [x] 2.2 在 `LineService._action_remove_item` 調用 `emit_order_update()`
- [x] 2.3 在 `LineService._action_cancel_order` 調用 `emit_order_update()`
- [x] 2.4 在 `LineService._action_update_order` 調用 `emit_order_update()`
- **驗證**: 在 LINE 群組點餐，開啟看板頁面確認即時更新

## 3. 聊天訊息廣播整合

- [x] 3.1 在 `LineService._handle_group_message` 調用 `emit_chat_message()`
  - 使用者訊息：在處理後廣播
  - AI 回覆：在回覆後廣播
- **驗證**: 在 LINE 群組發訊息，開啟看板頁面確認「美食評論區」即時更新

## 4. Session 狀態廣播整合

- [x] 4.1 在 `LineService._start_ordering` 調用 `emit_session_status()`
- [x] 4.2 在 `LineService._end_ordering` 調用 `emit_session_status()`
- **驗證**: 在 LINE 群組開單/收單，看板頁面即時反映狀態

## 5. 付款狀態廣播整合

- [x] 5.1 在 `OrderService.mark_paid` 調用 `emit_payment_update()`
- [x] 5.2 在 `OrderService.refund` 調用 `emit_payment_update()`
- **驗證**: 在管理員頁面標記付款，看板頁面即時更新

## 6. 今日店家變更廣播整合

- [x] 6.1 在 `admin.py` 的 `set_group_today_stores` API 調用 `emit_store_change()`
- [x] 6.2 在 `line_admin.py` 的 `set_group_today_store` API 調用 `emit_store_change()`
- **驗證**: 設定今日店家，看板頁面即時更新店家名稱

## 7. 超級管理員代理點餐 API

- [x] 7.1 在 `admin.py` 新增 `POST /api/admin/groups/{group_id}/proxy-orders`
  - 驗證群組有進行中的 Session
  - 驗證使用者存在
  - 調用 `OrderService.create_order()`
  - 調用 `emit_order_update()`
- [x] 7.2 在 `admin.py` 新增 `PUT /api/admin/groups/{group_id}/proxy-orders/{order_id}`
  - 驗證訂單存在
  - 調用 `OrderService.update_order()`
  - 調用 `emit_order_update()`
- **驗證**: 在管理員頁面使用代理點餐功能

## 8. 清除 Session 訂單 API

- [x] 8.1 在 `OrderService` 新增 `clear_session_orders()` 方法
- [x] 8.2 在 `admin.py` 新增 `DELETE /api/admin/sessions/{session_id}/orders`
  - 驗證 Session 存在
  - 調用 `OrderService.clear_session_orders()`
  - 調用 `emit_order_update()` (action: "cleared")
- **驗證**: 在管理員頁面清除訂單，看板頁面即時更新

## 9. 前端事件監聽更新

- [x] 9.1 更新 `board.html` 監聽新事件
  - `session_status` - 更新 Session 狀態顯示
  - `payment_update` - 更新付款狀態標記
  - `store_change` - 更新店家名稱
- [x] 9.2 更新 `admin.html` 監聯新事件（如需要）
- **驗證**: 所有事件在前端正確處理並更新 UI
