## 1. broadcast.py 核心修改

- [x] 1.1 新增 `PendingEvent` dataclass
- [x] 1.2 新增 `_event_queue` ContextVar
- [x] 1.3 新增 `_get_queue()` helper
- [x] 1.4 新增 `_queue_event()` 函數
- [x] 1.5 新增 `flush_events()` 函數
- [x] 1.6 新增 `clear_events()` 函數
- [x] 1.7 新增 `commit_and_notify(db)` helper
- [x] 1.8 修改 `register_broadcasters()` 建立事件類型映射表
- [x] 1.9 修改所有 `emit_*` 函數改為呼叫 `_queue_event()`

## 2. admin.py Router 更新

- [x] 2.1 新增 `from app.broadcast import commit_and_notify`
- [x] 2.2 `create_store` (line ~216) - 改用 `commit_and_notify(db)`
- [x] 2.3 `update_store` (line ~252) - 改用 `commit_and_notify(db)`
- [x] 2.4 `delete_store` (line ~283) - 改用 `commit_and_notify(db)`
- [x] 2.5 `set_today_stores` (line ~703) - 改用 `commit_and_notify(db)`
- [x] 2.6 `create_proxy_order` (line ~924) - 改用 `commit_and_notify(db)`
- [x] 2.7 `update_proxy_order` (line ~1013) - 改用 `commit_and_notify(db)`
- [x] 2.8 `mark_order_paid`, `refund_order`, `clear_session_orders` - 新增 `commit_and_notify(db)`

## 3. line_admin.py Router 更新

- [x] 3.1 新增 `from app.broadcast import commit_and_notify`
- [x] 3.2 `mark_order_paid` (line ~375) - 改用 `commit_and_notify(db)`
- [x] 3.3 `change_group_code` (line ~418) - 無需 emit（不涉及即時更新）
- [x] 3.4 `set_today_stores` (line ~338) - 改用 `commit_and_notify(db)`
- [x] 3.5 `create_store` (line ~486) - 改用 `commit_and_notify(db)`
- [x] 3.6 `update_store` (line ~537) - 改用 `commit_and_notify(db)`
- [x] 3.7 `delete_store` (line ~582) - 改用 `commit_and_notify(db)`

## 4. chat.py Router 更新

- [x] 4.1 新增 `from app.broadcast import commit_and_notify, emit_store_change`
- [x] 4.2 `_execute_actions` 後呼叫 `await commit_and_notify(db)`

## 5. line_service.py 更新

- [x] 5.1 新增 `from app.broadcast import flush_events`（各方法內引入）
- [x] 5.2 `_try_set_store_by_keyword` 方法 - 在 commit 後加 `await flush_events()`
- [x] 5.3 `_set_today_store` 方法 - 在 commit 後加 `await flush_events()`
- [x] 5.4 `_add_today_store` 方法 - 在 commit 後加 `await flush_events()`
- [x] 5.5 `_remove_today_store` 方法 - 在 commit 後加 `await flush_events()`
- [x] 5.6 `_clear_today_stores` 方法 - 在 commit 後加 `await flush_events()`
- [x] 5.7 `_start_ordering` 方法 - 在 commit 後加 `await flush_events()`
- [x] 5.8 `_end_ordering` 方法 - 在 commit 後加 `await flush_events()`
- [x] 5.9 `_execute_group_actions` 方法 - 在 commit 後加 `await flush_events()`

## 6. order_service.py 更新

- [x] 6.1 `mark_paid` - router (admin.py) 負責 `commit_and_notify(db)`
- [x] 6.2 `refund` - router (admin.py) 負責 `commit_and_notify(db)`
- [x] 6.3 `clear_session_orders` - router (admin.py) 負責 `commit_and_notify(db)`
- [x] 6.4 Service 層 emit 函數只 queue 事件，由 router 層統一 commit + flush

## 7. 驗證

- [x] 7.1 Python 語法驗證通過
- [x] 7.2 Event Queue 機制單元測試通過
- [x] 7.3 所有模組 import 測試通過
- [ ] 7.4 測試設定今日店家功能 - 應即時更新
- [ ] 7.5 測試新增/編輯/刪除店家功能 - 應即時更新
- [ ] 7.6 測試 LINE 開單/收單功能 - 應即時更新
