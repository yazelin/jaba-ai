# Proposal: add-input-sanitization

## Summary

新增 AI 輸入過濾機制，防止 prompt injection 攻擊，並記錄可疑輸入供超級管理員審查。

## Motivation

目前使用者輸入直接傳送給 AI，可能遭受 prompt injection 攻擊：
- 使用者可能透過特殊字元（如 `< >`、` ``` `）試圖注入惡意指令
- 過長的訊息可能是攻擊嘗試
- 缺乏攻擊記錄，無法追蹤可疑行為

## Scope

### In Scope
- 建立輸入過濾函數（移除 XML 標籤、markdown code blocks、過長訊息截斷）
- 新增 `security_logs` 資料表記錄可疑輸入
- 超級管理員後台新增安全日誌查看 API
- 記錄完整原始訊息和使用者資訊

### Out of Scope
- 關鍵詞過濾（可能誤殺正常訊息）
- 自動封鎖機制（由超管人工判斷）
- 前端日誌查看介面（僅提供 API）

## Approach

1. **輸入過濾**：在 `ai_service.chat()` 呼叫前過濾訊息
   - 長度限制 200 字元
   - 移除 XML/HTML 標籤 `<...>`
   - 移除 markdown code blocks ` ``` `
   - 移除連續分隔線 `---`、`===`

2. **安全日誌記錄**：當偵測到可疑輸入時
   - 記錄原始完整訊息（不截斷）
   - 記錄 LINE user_id、display_name
   - 記錄 group_id（如適用）
   - 記錄觸發原因（長度、標籤、code block 等）

3. **超管 API**：新增安全日誌查詢端點
   - 列出最近的可疑輸入記錄
   - 可依使用者或群組篩選

## Success Criteria

- 輸入過濾函數正確移除危險字元
- 可疑輸入完整記錄到資料庫
- 超管可透過 API 查詢安全日誌
