# Change: AI Log 新增 Token 計數欄位

## Why
目前 AI Log 記錄了執行時間，但缺少 token 數量資訊。新增 input_tokens 和 output_tokens 欄位可以：
- 更精確地分析 AI 使用成本
- 協助調整 prompt 長度
- 追蹤 token 使用趨勢

## What Changes
- 資料庫 `ai_logs` 表格新增 `input_tokens` 和 `output_tokens` 欄位
- AI 服務記錄時計算並儲存 token 數量（使用簡易估算）
- 前端 AI Log 詳情顯示 token 數量

## Impact
- Affected specs: database, admin
- Affected code:
  - `migrations/versions/003_add_ai_logs.py`
  - `app/models/system.py`
  - `app/services/ai_service.py`
  - `app/services/line_service.py`
  - `app/routers/chat.py`
  - `static/admin.html`
