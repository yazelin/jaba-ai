## 1. 資料庫變更
- [x] 1.1 更新 `migrations/versions/003_add_ai_logs.py` 新增 input_tokens, output_tokens 欄位
- [x] 1.2 更新 `app/models/system.py` AiLog model 新增欄位
- [x] 1.3 重建資料庫（drop + recreate ai_logs 表）

## 2. 服務層變更
- [x] 2.1 在 `app/services/ai_service.py` 新增 token 估算函數
- [x] 2.2 更新 ai_service.py 的 chat 方法回傳 token 數量
- [x] 2.3 更新 `app/services/line_service.py` 的 `_record_ai_log` 記錄 token
- [x] 2.4 更新 `app/routers/chat.py` 的 `_record_ai_log` 記錄 token

## 3. 前端變更
- [x] 3.1 更新 `static/admin.html` AI Log 詳情顯示 token 數量

## 4. 文檔更新
- [x] 4.1 更新 `docs/database.md` ai_logs 表格說明
- [x] 4.2 更新 `docs/architecture.md` AI 可觀測性說明
