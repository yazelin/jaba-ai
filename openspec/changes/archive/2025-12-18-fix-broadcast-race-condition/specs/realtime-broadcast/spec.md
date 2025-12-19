# realtime-broadcast Spec Delta

## ADDED Requirements

### Requirement: 事件隊列機制
系統 SHALL 使用 request-scoped 事件隊列來確保 Socket.IO 廣播在資料庫 commit 之後才發送。

#### Scenario: 事件加入隊列
- **GIVEN** 任何 API endpoint 處理過程中
- **WHEN** 呼叫 `emit_*` 函數（如 `emit_order_update`、`emit_payment_update`）
- **THEN** 事件被加入當前請求的隊列
- **AND** 事件不會立即發送到 Socket.IO

#### Scenario: 資料庫提交後發送事件
- **GIVEN** 請求處理過程中有事件被加入隊列
- **WHEN** 呼叫 `commit_and_notify(db)` 函數
- **THEN** 系統先執行 `db.commit()` 提交資料庫變更
- **AND** 然後依序發送隊列中的所有事件
- **AND** 清空隊列

#### Scenario: 錯誤時清空隊列
- **GIVEN** 請求處理過程中有事件被加入隊列
- **WHEN** 發生錯誤導致 rollback
- **THEN** 呼叫 `clear_events()` 清空隊列
- **AND** 不發送任何事件

### Requirement: 前端即時資料一致性
系統 SHALL 確保前端收到 Socket.IO 通知後能取得最新資料。

#### Scenario: 前端收到通知後取得最新資料
- **GIVEN** 前端正在監聽 Socket.IO 事件
- **WHEN** 前端收到任何廣播事件
- **AND** 前端立即發起 API 請求取得資料
- **THEN** 前端取得的資料一定包含觸發該事件的變更
