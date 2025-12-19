## ADDED Requirements

### Requirement: LINE Webhook Integration
系統 SHALL 整合 LINE Webhook 接收和處理訊息。

#### Scenario: Webhook 驗證
- **WHEN** LINE Platform 發送 Webhook
- **THEN** 系統驗證 X-Line-Signature 簽章

#### Scenario: 文字訊息處理
- **WHEN** 收到文字訊息
- **THEN** 系統根據訊息內容和群組狀態進行處理

#### Scenario: Leave 事件處理
- **WHEN** Bot 被踢出群組
- **THEN** 系統更新群組狀態

### Requirement: Group Ordering Session
系統 SHALL 管理群組點餐 Session。

#### Scenario: 開始點餐
- **WHEN** 使用者在已啟用群組中說「開單」
- **THEN** 系統建立 Session 並顯示今日菜單

#### Scenario: 點餐處理
- **WHEN** Session 進行中且使用者發送訊息
- **THEN** AI 解析訊息並執行訂單操作

#### Scenario: 結束點餐
- **WHEN** 使用者說「收單」
- **THEN** 系統結束 Session 並顯示訂單摘要

### Requirement: Order Operations
系統 SHALL 支援透過自然語言進行訂單操作。

#### Scenario: 建立訂單
- **WHEN** 使用者說「我要雞腿便當」
- **THEN** AI 解析並建立訂單

#### Scenario: 修改訂單
- **WHEN** 使用者說「改排骨」
- **THEN** AI 解析並修改使用者的訂單

#### Scenario: 取消訂單
- **WHEN** 使用者說「不要了」
- **THEN** AI 解析並取消使用者的訂單

#### Scenario: 跟單
- **WHEN** 使用者說「+1」或「我也要」
- **THEN** AI 複製最近的訂單給該使用者

### Requirement: Personal Preference Setting
系統 SHALL 支援 1v1 聊天中設定個人偏好。

#### Scenario: 設定稱呼
- **WHEN** 使用者在 1v1 說「叫我小明」
- **THEN** 系統儲存使用者的偏好稱呼

#### Scenario: 設定飲食偏好
- **WHEN** 使用者在 1v1 說「我不吃辣」
- **THEN** 系統儲存使用者的飲食限制

#### Scenario: 套用偏好
- **WHEN** 使用者在群組點餐
- **THEN** AI 參考個人偏好進行提醒

### Requirement: Status Query
系統 SHALL 支援使用者查詢群組啟用狀態。

#### Scenario: 查詢狀態
- **WHEN** 使用者輸入「jaba」或相關指令
- **THEN** 系統回應群組的啟用狀態

#### Scenario: 未啟用提示
- **WHEN** 使用者在未啟用群組嘗試點餐
- **THEN** 系統提示群組尚未啟用，需申請
