# personal-chat Specification

## Purpose
TBD - created by archiving change add-personal-chat-features. Update Purpose after archive.
## Requirements
### Requirement: Personal Chat Query Functions
系統 SHALL 支援 1v1 聊天中查詢個人資訊。

#### Scenario: 查詢偏好設定
- **GIVEN** 使用者已設定個人偏好
- **WHEN** 使用者在 1v1 輸入「我的設定」或相關詢問
- **THEN** 系統顯示使用者目前的偏好設定內容
  - 包含：稱呼、飲食限制、口味偏好等
  - 若無設定則顯示「尚未設定偏好」

#### Scenario: 查詢所屬群組
- **GIVEN** 使用者已加入一或多個群組
- **WHEN** 使用者在 1v1 輸入「我的群組」或相關詢問
- **THEN** 系統顯示使用者所屬的已啟用群組列表
  - 包含：群組名稱、加入時間
  - 只顯示 status='active' 的群組
  - 若無所屬群組則顯示「您尚未加入任何群組」

#### Scenario: 查詢歷史訂單
- **GIVEN** 使用者有歷史訂單紀錄
- **WHEN** 使用者在 1v1 輸入「歷史訂單」或相關詢問
- **THEN** 系統顯示使用者最近 10 筆訂單紀錄
  - 包含：日期、群組名稱、店家名稱、品項、金額
  - 按時間倒序排列（最新在前）
  - 若無訂單則顯示「您尚無訂單紀錄」

### Requirement: Personal Preference Management
系統 SHALL 支援 1v1 聊天中管理個人偏好。

#### Scenario: 清除偏好設定
- **WHEN** 使用者在 1v1 輸入「清除設定」或相關請求
- **THEN** 系統清除使用者所有偏好設定
- **AND** 系統回應確認訊息「已清除您的偏好設定」

### Requirement: Personal Quick Commands
系統 SHALL 支援個人模式快捷指令。

#### Scenario: 快捷指令列表
系統支援以下快捷指令：
- 「我的設定」- 查詢偏好設定
- 「我的群組」- 查詢所屬群組
- 「歷史訂單」- 查詢歷史訂單
- 「清除設定」- 清除偏好設定

#### Scenario: AI 自然語言理解
- **WHEN** 使用者用自然語言表達查詢意圖
- **THEN** AI 應理解並執行對應的查詢動作
- 例如：
  - 「我設定了什麼」→ 查詢偏好設定
  - 「我加入了哪些群組」→ 查詢所屬群組
  - 「之前點過什麼」→ 查詢歷史訂單
  - 「把我的資料都刪掉」→ 清除偏好設定

