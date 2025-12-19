# Tasks

## Phase 1: 資料庫與模型

- [x] 1.1 新增 `AiLog` 模型到 `app/models/system.py`
  - 欄位：id, created_at, user_id, group_id, model, input_prompt, raw_response, parsed_message, parsed_actions, duration_ms
- [x] 1.2 新增 Alembic migration 建立 `ai_logs` 資料表
- [x] 1.3 新增 `AiLogRepository` 到 `app/repositories/system_repo.py`
  - create, get_list (分頁), get_by_id

## Phase 2: AI Service 修改

- [x] 2.1 修改 `_parse_response` 方法擷取最後一段 JSON
  - 優先擷取最後一段 ` ```json ``` ` code block
  - Fallback：尋找最後一個裸 JSON 物件
- [x] 2.2 修改 `chat` 方法記錄 AI Log
  - 記錄完整輸入 prompt
  - 記錄原始回應
  - 記錄解析結果
  - 記錄執行時間

## Phase 3: 後端 API

- [x] 3.1 新增 AI Log API endpoints 到 `app/routers/admin.py`
  - GET /api/admin/ai-logs - 列表（分頁、篩選）
  - GET /api/admin/ai-logs/{id} - 詳情

## Phase 4: 前端 UI

- [x] 4.1 在 `static/admin.html` 新增 AI Log 分頁
  - 列表顯示：時間、使用者、群組、訊息摘要
  - 詳情彈窗：完整輸入、思考過程、解析結果
  - 篩選：時間範圍、群組

## Phase 5: 驗證

- [x] 5.1 測試 JSON 擷取邏輯
  - 測試包含思考過程的回應
  - 測試純 JSON 回應
  - 測試多個 code block 的情況
- [x] 5.2 測試 AI Log 記錄與查看功能
