## ADDED Requirements

### Requirement: Dashboard Display
系統 SHALL 提供看板頁面，顯示群組的訂單彙總和聊天記錄，UI 風格與原 jaba 專案一致。

#### Scenario: 看板載入
- **WHEN** 使用者存取看板頁面
- **THEN** 系統顯示今日店家資訊、訂單列表、聊天記錄、品項統計

#### Scenario: 群組選擇
- **WHEN** 使用者在看板選擇不同群組
- **THEN** 系統顯示該群組的訂單和聊天記錄

#### Scenario: 即時更新
- **WHEN** 有新訂單或聊天訊息
- **THEN** 看板透過 Socket.IO 即時更新顯示

### Requirement: Brand Identity
系統 SHALL 保留呷爸品牌識別，包含 Logo、圖示、視覺風格。

#### Scenario: 圖示顯示
- **WHEN** 載入任何頁面
- **THEN** 系統顯示 jaba 品牌 icon（jaba-sm.png）

#### Scenario: 視覺一致性
- **WHEN** 顯示任何 UI 元件
- **THEN** 視覺風格與原 jaba 專案保持一致

### Requirement: Store Management
系統 SHALL 提供店家管理功能，包含新增、編輯、啟用/停用店家。

#### Scenario: 新增店家
- **WHEN** 管理員輸入店家資訊
- **THEN** 系統建立新店家記錄

#### Scenario: 菜單辨識
- **WHEN** 管理員上傳菜單圖片
- **THEN** 系統使用 AI 辨識菜單內容並建立結構化資料

#### Scenario: 菜單差異預覽
- **WHEN** AI 辨識菜單完成
- **THEN** 系統顯示與現有菜單的差異（新增/修改/刪除項目）

### Requirement: Order Tracking
系統 SHALL 追蹤群組訂單狀態，包含訂單明細和付款狀態。

#### Scenario: 訂單統計
- **WHEN** 查看群組訂單
- **THEN** 系統顯示訂單數量、品項統計、總金額

#### Scenario: 付款追蹤
- **WHEN** 管理員標記已付款
- **THEN** 系統更新訂單付款狀態並廣播更新

### Requirement: Real-time Communication
系統 SHALL 使用 Socket.IO 提供即時通訊功能。

#### Scenario: 訂單廣播
- **WHEN** 訂單建立或更新
- **THEN** 系統廣播 group_order_updated 事件

#### Scenario: 聊天廣播
- **WHEN** 有新聊天訊息
- **THEN** 系統廣播 group_chat_updated 事件

#### Scenario: 店家變更廣播
- **WHEN** 今日店家變更
- **THEN** 系統廣播 store_changed 事件
