# Realtime Broadcast Specification

## ADDED Requirements

### Requirement: 訂單變更即時廣播
系統 SHALL 在訂單資料變更時，透過 Socket.IO 廣播通知所有連線的客戶端。

#### Scenario: 新增訂單時廣播
- **WHEN** 使用者透過 LINE 或管理員代理建立訂單
- **THEN** 系統發送 `order_update` 事件到該群組的 room 和 `board:all` room
- **AND** 事件資料包含 `group_id`、`action: "created"`、`order` 摘要

#### Scenario: 修改訂單時廣播
- **WHEN** 訂單品項被修改或刪除
- **THEN** 系統發送 `order_update` 事件
- **AND** 事件資料包含 `action: "updated"` 或 `action: "deleted"`

#### Scenario: 取消訂單時廣播
- **WHEN** 使用者取消整筆訂單
- **THEN** 系統發送 `order_update` 事件
- **AND** 事件資料包含 `action: "cancelled"`、`user_id`

### Requirement: 聊天訊息即時廣播
系統 SHALL 在群組對話發生時，透過 Socket.IO 廣播通知所有連線的客戶端。

#### Scenario: 使用者訊息廣播
- **WHEN** 使用者在 LINE 群組發送訊息
- **THEN** 系統發送 `chat_message` 事件
- **AND** 事件資料包含 `group_id`、`user_id`、`display_name`、`content`、`role: "user"`

#### Scenario: AI 回覆訊息廣播
- **WHEN** AI 回覆群組訊息
- **THEN** 系統發送 `chat_message` 事件
- **AND** 事件資料包含 `role: "assistant"`、`content`

### Requirement: Session 狀態即時廣播
系統 SHALL 在群組開單或收單時，透過 Socket.IO 廣播通知所有連線的客戶端。

#### Scenario: 開單廣播
- **WHEN** 群組開始點餐（建立新 OrderSession）
- **THEN** 系統發送 `session_status` 事件
- **AND** 事件資料包含 `group_id`、`status: "ordering"`、`session_id`

#### Scenario: 收單廣播
- **WHEN** 群組結束點餐（OrderSession 狀態變為 ended）
- **THEN** 系統發送 `session_status` 事件
- **AND** 事件資料包含 `status: "ended"`、`summary`（訂單摘要）

### Requirement: 付款狀態即時廣播
系統 SHALL 在訂單付款狀態變更時，透過 Socket.IO 廣播通知所有連線的客戶端。

#### Scenario: 標記已付款廣播
- **WHEN** 管理員將訂單標記為已付款
- **THEN** 系統發送 `payment_update` 事件
- **AND** 事件資料包含 `order_id`、`payment_status: "paid"`

#### Scenario: 退款廣播
- **WHEN** 管理員將訂單標記為退款
- **THEN** 系統發送 `payment_update` 事件
- **AND** 事件資料包含 `payment_status: "refunded"`

### Requirement: 今日店家變更即時廣播
系統 SHALL 在群組今日店家設定變更時，透過 Socket.IO 廣播通知所有連線的客戶端。

#### Scenario: 設定今日店家廣播
- **WHEN** 管理員設定群組的今日店家
- **THEN** 系統發送 `store_change` 事件
- **AND** 事件資料包含 `group_id`、`stores` 列表
