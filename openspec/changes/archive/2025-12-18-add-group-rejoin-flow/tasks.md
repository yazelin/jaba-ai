## 1. 實作群組重新加入流程

- [x] 1.1 修改 `handle_join` 檢測群組狀態，若為 "inactive" 則發送選擇訊息
- [x] 1.2 設計選擇訊息內容，使用 LINE Flex Message 或 Quick Reply 按鈕
- [x] 1.3 新增 Postback 處理：`action=rejoin_restore` 和 `action=rejoin_reapply`
- [x] 1.4 實作「恢復舊設定」邏輯：將 status 改為 "active"
- [x] 1.5 實作「重新申請」邏輯：將 status 改為 "pending"

## 2. 更新離開群組處理

- [x] 2.1 確認 `handle_leave` 正確設定 status 為 "inactive"（已實作）

## 3. 測試驗證

- [x] 3.1 測試 Bot 被踢出後重新加入的流程
- [x] 3.2 測試選擇「恢復舊設定」後功能正常
- [x] 3.3 測試選擇「重新申請」後需重新審核
