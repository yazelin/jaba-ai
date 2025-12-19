# Tasks: add-input-sanitization

## Phase 1: 資料庫架構

- [x] 1.1 新增 `SecurityLog` model (`app/models/system.py`)
  - id (UUID)
  - line_user_id (String)
  - display_name (String, nullable)
  - line_group_id (String, nullable)
  - original_message (Text) - 完整原始訊息
  - sanitized_message (Text) - 過濾後訊息
  - trigger_reasons (JSONB) - 觸發原因列表
  - context_type (String) - group/personal
  - created_at (DateTime)

- [x] 1.2 新增 `SecurityLogRepository` (`app/repositories/system_repo.py`)
  - create()
  - get_recent(limit, offset)
  - get_by_user(line_user_id)
  - get_by_group(line_group_id)
  - get_stats()

- [x] 1.3 建立 Alembic migration 新增 `security_logs` 資料表
  - 建立 `migrations/versions/003_add_security_logs.py`

## Phase 2: 輸入過濾服務

- [x] 2.1 建立 `sanitize_user_input()` 函數 (`app/services/ai_service.py`)
  - 參數: text, max_length=200
  - 回傳: (sanitized_text, trigger_reasons)
  - 過濾規則:
    - 長度超過 max_length 截斷
    - 移除 XML/HTML 標籤 `<[^>]*>`
    - 移除 markdown code blocks
    - 移除連續分隔線 `[-=]{3,}`

- [x] 2.2 整合至 `LineService`
  - 在呼叫 `ai_service.chat()` 前過濾
  - 若有觸發原因，記錄安全日誌
  - 整合點:
    - `_handle_personal_chat()` (line 258)
    - `_handle_active_group_chat()` (line 1410)
    - `_handle_application_with_ai()` (line 1902)
  - 新增 `_log_security_event()` 方法

## Phase 3: 超管 API

- [x] 3.1 新增安全日誌 API (`app/routers/admin.py`)
  - GET `/api/admin/security-logs` - 列出日誌
    - 參數: limit, offset, line_user_id, line_group_id
  - GET `/api/admin/security-logs/stats` - 統計資訊
    - 回傳: 總數、依觸發原因分類統計、每日統計

## Phase 4: 自動封鎖機制

- [x] 4.1 新增環境變數設定 (`app/config.py`)
  - `SECURITY_BAN_THRESHOLD` - 封鎖閾值（預設 5 次）

- [x] 4.2 User model 新增封鎖欄位 (`app/models/user.py`)
  - `is_banned` (Boolean, default False)
  - `banned_at` (DateTime, nullable)

- [x] 4.3 建立 Alembic migration 新增欄位
  - 建立 `migrations/versions/004_add_user_ban_fields.py`

- [x] 4.4 `_log_security_event()` 中實作自動封鎖
  - 記錄日誌後檢查違規次數
  - 超過閾值自動設定 `is_banned = True`

- [x] 4.5 `handle_message()` 中檢查封鎖狀態
  - 被封鎖使用者的訊息靜默忽略（不回應）

## Validation

- [x] 測試過濾函數正確移除各類危險字元
- [x] 測試長訊息正確截斷但完整記錄原始內容
- [x] 測試 API 正確回傳日誌記錄
- [x] 測試達到閾值後自動封鎖
- [x] 測試封鎖後訊息不回應
