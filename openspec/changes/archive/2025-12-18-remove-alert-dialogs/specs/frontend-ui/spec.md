## ADDED Requirements

### Requirement: Detail Modal Component
前端頁面 SHALL 提供通用的詳情 Modal 元件，用於顯示多行資訊內容。

#### Scenario: Display user details
- **WHEN** 管理員點擊「查看」使用者詳情按鈕
- **THEN** 系統顯示 Modal 對話框包含使用者資訊
- **AND** Modal 可透過點擊關閉按鈕或背景關閉

#### Scenario: Display group details
- **WHEN** 管理員點擊「查看」群組詳情按鈕
- **THEN** 系統顯示 Modal 對話框包含群組資訊和成員列表
- **AND** Modal 可透過點擊關閉按鈕或背景關閉

#### Scenario: Display AI correction log
- **WHEN** 管理員點擊 AI 修正紀錄的「查看」按鈕
- **THEN** 系統顯示 Modal 對話框包含原始訊息內容

### Requirement: Notification System
前端頁面 SHALL 使用 `showNotification()` 函數顯示簡短回饋訊息，支援 success 和 error 兩種類型。

#### Scenario: Show success notification
- **WHEN** 操作成功完成
- **THEN** 系統顯示綠色邊框的通知訊息
- **AND** 通知在 3 秒後自動消失

#### Scenario: Show error notification
- **WHEN** 操作失敗或驗證錯誤
- **THEN** 系統顯示紅色邊框的通知訊息
- **AND** 通知在 3 秒後自動消失

### Requirement: Confirm Dialog Component
前端頁面 SHALL 使用自訂 Modal 對話框取代原生 `confirm()`，提供 Promise-based 的 `showConfirm()` 函數。

#### Scenario: Confirm dangerous action
- **WHEN** 使用者執行刪除或不可逆操作
- **THEN** 系統顯示確認對話框
- **AND** 使用者可選擇確認或取消
