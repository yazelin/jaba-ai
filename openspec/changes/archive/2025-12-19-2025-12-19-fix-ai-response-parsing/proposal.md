# Proposal: Fix AI Response JSON Extraction & Add AI Log Viewer

## Problem Statement

AI Agent 回應中包含思考過程和 JSON 格式的最終回應，但目前的解析邏輯無法正確擷取 JSON 部分，導致整個回應（包含思考過程）被當作訊息發送給使用者。此外，缺乏 AI 對話日誌機制，難以分析和調整 prompt。

### 觀察到的問題

1. **AI 回應格式**：AI 會先輸出思考過程，然後在最後用 markdown code block 包裹 JSON 回應
2. **現有擷取邏輯不足**：無法正確擷取最後一段 JSON code block
3. **缺乏日誌記錄**：無法查看 AI 的完整輸入（prompt context）與輸出（思考過程），難以分析和調整 prompt

### 影響

- 使用者收到非常長的訊息（包含 AI 的思考過程）
- Actions 沒有被正確執行
- 無法追蹤和分析 AI 行為

## Solution

### 1. 改進 JSON 擷取邏輯

擷取策略（按優先順序）：
1. **優先擷取最後一段 ` ```json ``` ` code block** - AI 的最終回應通常在最後
2. **Fallback：尋找最後一個裸 JSON 物件** - 若無 code block

### 2. 新增 AI Log 資料表

建立 `ai_logs` 資料表，成對記錄：
- **輸入**：完整的 prompt context（system prompt + context + history + user message）
- **輸出**：AI 的原始回應（包含思考過程）
- **解析結果**：提取的 message 和 actions
- **Metadata**：時間戳、使用者、群組、模型等

### 3. 超級管理員 AI Log 分頁

在超管後台新增 AI Log 分頁：
- 列表顯示 AI 對話記錄（時間、使用者、群組、訊息摘要）
- 點擊查看詳情：完整輸入、思考過程、解析結果
- 篩選功能：依時間、群組、使用者篩選

## Scope

- `app/services/ai_service.py` - 修改 `_parse_response` 方法、新增日誌記錄
- `app/models/system.py` - 新增 `AiLog` 模型
- `app/repositories/system_repo.py` - 新增 AI Log 相關方法
- `app/routers/admin.py` - 新增 AI Log API endpoints
- `static/admin.html` - 新增 AI Log 分頁
- `migrations/versions/` - 新增 migration

## Out of Scope

- 修改 AI 提示詞（保留思考過程輸出）
- 菜單辨識功能的日誌記錄

## Success Criteria

- 即使 AI 輸出思考過程，仍能正確擷取最後一段 JSON 回應
- Actions 正確執行（點餐成功建立）
- 使用者只收到 JSON 中的 message，不包含思考過程
- AI 對話完整記錄到資料庫（輸入 + 輸出成對）
- 超管後台可查看 AI Log 並進行篩選分析
