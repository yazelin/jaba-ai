# database Specification

## Purpose
TBD - created by archiving change integrate-jaba-projects. Update Purpose after archive.
## Requirements
### Requirement: PostgreSQL Database
系統 SHALL 使用 PostgreSQL 作為主要資料儲存，透過 asyncpg 進行非同步存取。

#### Scenario: 資料庫連線
- **WHEN** 應用程式啟動
- **THEN** 系統建立與 PostgreSQL 的非同步連線池

#### Scenario: 資料表建立
- **WHEN** 執行 Alembic migration
- **THEN** 系統建立所有必要的資料表和索引

### Requirement: User Data Model
系統 SHALL 儲存使用者資料，包含 LINE User ID、顯示名稱、個人偏好。刪除使用者時直接從資料庫移除。

#### Scenario: 使用者首次互動
- **WHEN** 使用者首次與 Bot 互動
- **THEN** 系統自動建立使用者記錄，儲存 LINE User ID 和顯示名稱

#### Scenario: 個人偏好儲存
- **WHEN** 使用者設定個人偏好（稱呼、飲食限制、過敏、飲料偏好）
- **THEN** 系統將偏好儲存為 JSONB 格式

#### Scenario: 使用者刪除
- **WHEN** 系統需要刪除使用者
- **THEN** 系統直接從資料庫移除使用者記錄（硬刪除）

### Requirement: Group Data Model
系統 SHALL 儲存群組資料，包含 LINE Group ID、群組名稱、狀態。刪除群組時直接從資料庫移除。

#### Scenario: 群組狀態管理
- **WHEN** 群組申請審核通過
- **THEN** 群組狀態從 pending 變更為 active

#### Scenario: 群組成員追蹤
- **WHEN** 使用者在群組中互動
- **THEN** 系統記錄使用者為該群組成員

#### Scenario: 群組刪除
- **WHEN** 管理員刪除群組
- **THEN** 系統直接從資料庫移除群組記錄（硬刪除）

### Requirement: Store Data Model
系統 SHALL 儲存店家資料，包含名稱、電話、地址、描述、狀態。刪除店家時直接從資料庫移除。

#### Scenario: 店家全域共用
- **WHEN** 管理員建立新店家
- **THEN** 所有群組都可以將該店家設為今日店家

#### Scenario: 店家刪除
- **WHEN** 管理員刪除店家
- **THEN** 系統直接從資料庫移除店家記錄（硬刪除）

### Requirement: Menu Data Model
系統 SHALL 儲存菜單資料，包含分類、品項、價格、變體、促銷。

#### Scenario: 菜單品項儲存
- **WHEN** 管理員儲存菜單
- **THEN** 系統儲存品項名稱、價格、分類、尺寸變體（JSONB）、促銷資訊（JSONB）

### Requirement: Order Session Data Model
系統 SHALL 儲存點餐 Session 資料，以群組為單位管理。

#### Scenario: Session 建立
- **WHEN** 使用者在群組中說「開單」
- **THEN** 系統建立新的 order_session 記錄，狀態為 ordering

#### Scenario: Session 結束
- **WHEN** 使用者說「收單」
- **THEN** 系統更新 order_session 狀態為 ended

### Requirement: Order Data Model
系統 SHALL 儲存訂單資料，包含使用者、品項、金額、付款狀態。

#### Scenario: 訂單品項儲存
- **WHEN** 使用者點餐
- **THEN** 系統儲存訂單品項，包含名稱、數量、單價、客製化選項（JSONB）

### Requirement: Group Today Store
系統 SHALL 以群組為單位儲存今日店家設定。

#### Scenario: 設定今日店家
- **WHEN** 群組管理員設定今日店家
- **THEN** 系統儲存 group_id, store_id, date 的關聯

#### Scenario: 多店家支援
- **WHEN** 群組管理員設定多個今日店家
- **THEN** 系統允許同一群組同一天有多個今日店家

### Requirement: Chat Message Storage
系統 SHALL 儲存對話記錄用於 AI 上下文和看板顯示。

#### Scenario: 群組對話儲存
- **WHEN** 群組中發生對話
- **THEN** 系統儲存訊息並關聯到群組和使用者

### Requirement: AI Prompt Storage
系統 SHALL 將 AI 提示詞儲存在資料庫中，便於管理和更新。

#### Scenario: 提示詞載入
- **WHEN** AI 服務需要提示詞
- **THEN** 系統從資料庫載入對應的提示詞內容

### Requirement: AI Log Storage
系統 SHALL 儲存 AI 對話日誌，包含完整輸入（prompt context）與輸出（原始回應），以及 token 使用量，供分析和調整 prompt 使用。

#### Scenario: 記錄 AI 對話
- **WHEN** AI 服務處理使用者訊息
- **THEN** 系統儲存完整的 prompt context（system prompt + context + history + user message）、AI 原始回應（包含思考過程）、解析結果（message + actions）、執行時間、輸入 token 數量、輸出 token 數量

#### Scenario: AI Log 欄位
- **WHEN** 儲存 AI Log
- **THEN** 記錄包含：id (UUID), created_at, user_id (nullable), group_id (nullable), model (varchar), input_prompt (text), raw_response (text), parsed_message (text), parsed_actions (jsonb), duration_ms (int), success (boolean), input_tokens (int), output_tokens (int)

#### Scenario: AI Log 查詢
- **WHEN** 管理員查詢 AI Log
- **THEN** 系統支援依時間範圍、群組、使用者篩選，並支援分頁

