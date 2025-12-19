# admin Specification Delta

## ADDED Requirements

### Requirement: AI Log Viewer
系統 SHALL 提供 AI 對話日誌檢視功能，供超級管理員分析 AI 行為和調整 prompt。

#### Scenario: AI Log 列表
- **WHEN** 超級管理員進入 AI Log 分頁
- **THEN** 系統顯示 AI 對話記錄列表，包含時間、使用者名稱、群組名稱、使用者輸入摘要、AI 回應摘要

#### Scenario: AI Log 詳情
- **WHEN** 超級管理員點擊某筆 AI Log
- **THEN** 系統顯示完整詳情：輸入的完整 prompt context、AI 原始回應（包含思考過程）、解析出的 message 和 actions、執行時間

#### Scenario: AI Log 篩選
- **WHEN** 超級管理員設定篩選條件
- **THEN** 系統支援依時間範圍、群組篩選 AI Log

#### Scenario: AI Log 分頁
- **WHEN** AI Log 記錄數量超過單頁上限
- **THEN** 系統提供分頁功能，預設每頁 20 筆
