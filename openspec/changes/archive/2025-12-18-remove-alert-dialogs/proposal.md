# Change: Remove all alert() dialogs from frontend

## Why
使用者體驗不佳：`alert()` 對話框會阻塞頁面操作，且外觀無法自訂，與現有 UI 風格不一致。

## What Changes
- 將所有 `alert()` 呼叫替換為自訂 UI 元件
- 簡單訊息使用現有的 `showNotification()` 函數
- 多行詳細資訊使用 Modal 對話框
- 統一 `board.html` 的 `showNotification()` 支援 error type

## Impact
- Affected code: `static/admin.html`, `static/board.html`
- No backend changes required
- No breaking changes
