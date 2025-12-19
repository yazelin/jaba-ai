# Admin Proxy Order Specification

## ADDED Requirements

### Requirement: 超級管理員代理建立訂單
系統 SHALL 提供 API 讓超級管理員代替使用者建立訂單。

#### Scenario: 代理建立訂單成功
- **WHEN** 超級管理員呼叫 `POST /api/admin/groups/{group_id}/proxy-orders`
- **AND** 請求包含有效的 `user_id` 和 `items` 列表
- **AND** 群組有進行中的 OrderSession
- **THEN** 系統為該使用者建立訂單
- **AND** 回傳 `{"success": true, "order_id": "..."}`
- **AND** 廣播 `order_update` 事件

#### Scenario: 代理建立訂單失敗 - 無進行中的 Session
- **WHEN** 超級管理員呼叫代理建立訂單 API
- **AND** 群組沒有進行中的 OrderSession
- **THEN** 系統回傳 400 錯誤
- **AND** 錯誤訊息為「群組沒有進行中的點餐」

#### Scenario: 代理建立訂單失敗 - 使用者不存在
- **WHEN** 超級管理員呼叫代理建立訂單 API
- **AND** 指定的 `user_id` 不存在
- **THEN** 系統回傳 404 錯誤
- **AND** 錯誤訊息為「找不到該使用者」

### Requirement: 超級管理員代理修改訂單
系統 SHALL 提供 API 讓超級管理員代替使用者修改訂單。

#### Scenario: 代理修改訂單成功
- **WHEN** 超級管理員呼叫 `PUT /api/admin/groups/{group_id}/proxy-orders/{order_id}`
- **AND** 請求包含新的 `items` 列表
- **THEN** 系統更新該訂單的品項
- **AND** 重新計算訂單總金額
- **AND** 回傳 `{"success": true}`
- **AND** 廣播 `order_update` 事件

#### Scenario: 代理修改訂單失敗 - 訂單不存在
- **WHEN** 超級管理員呼叫代理修改訂單 API
- **AND** 指定的 `order_id` 不存在
- **THEN** 系統回傳 404 錯誤
- **AND** 錯誤訊息為「找不到該訂單」

### Requirement: 超級管理員清除 Session 訂單
系統 SHALL 提供 API 讓超級管理員清除指定 Session 的所有訂單。

#### Scenario: 清除 Session 訂單成功
- **WHEN** 超級管理員呼叫 `DELETE /api/admin/sessions/{session_id}/orders`
- **THEN** 系統刪除該 Session 的所有訂單和訂單品項
- **AND** 回傳 `{"success": true, "deleted_count": N}`
- **AND** 廣播 `order_update` 事件（action: "cleared"）

#### Scenario: 清除 Session 訂單失敗 - Session 不存在
- **WHEN** 超級管理員呼叫清除 Session 訂單 API
- **AND** 指定的 `session_id` 不存在
- **THEN** 系統回傳 404 錯誤
- **AND** 錯誤訊息為「找不到該點餐 Session」
