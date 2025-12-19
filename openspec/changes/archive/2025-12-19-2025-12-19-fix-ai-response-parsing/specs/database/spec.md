# database Specification Delta

## ADDED Requirements

### Requirement: AI Log Storage
系統 SHALL 儲存 AI 對話日誌，包含完整輸入（prompt context）與輸出（原始回應），供分析和調整 prompt 使用。

#### Scenario: 記錄 AI 對話
- **WHEN** AI 服務處理使用者訊息
- **THEN** 系統儲存完整的 prompt context（system prompt + context + history + user message）、AI 原始回應（包含思考過程）、解析結果（message + actions）、執行時間

#### Scenario: AI Log 欄位
- **WHEN** 儲存 AI Log
- **THEN** 記錄包含：id (UUID), created_at, user_id (nullable), group_id (nullable), model (varchar), input_prompt (text), raw_response (text), parsed_message (text), parsed_actions (jsonb), duration_ms (int), success (boolean)

#### Scenario: AI Log 查詢
- **WHEN** 管理員查詢 AI Log
- **THEN** 系統支援依時間範圍、群組、使用者篩選，並支援分頁
