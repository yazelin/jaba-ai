## 1. admin.html 修改

- [x] 1.1 新增通用詳情 Modal 元件 (用於顯示使用者/群組詳情)
- [x] 1.2 新增 `showDetailModal(title, content)` 函數
- [x] 1.3 將 `viewUserDetail()` 的 alert 改為 Modal
- [x] 1.4 將 `viewGroupDetail()` 的 alert 改為 Modal
- [x] 1.5 將 AI 修正紀錄的「查看」按鈕改為 Modal
- [x] 1.6 新增確認對話框 Modal 元件
- [x] 1.7 新增 `showConfirm()` 函數 (Promise-based)
- [x] 1.8 將所有 `confirm()` 改為 `await showConfirm()`

## 2. board.html 修改

- [x] 2.1 更新 `showNotification()` 支援 error type
- [x] 2.2 將表單驗證的 alert 改為 `showNotification(msg, 'error')`
- [x] 2.3 將申請成功的 alert 改為 `showNotification()`
- [x] 2.4 將申請失敗的 alert 改為 `showNotification(msg, 'error')`

## 3. line-admin.html 修改

- [x] 3.1 新增確認對話框 Modal 元件
- [x] 3.2 新增 `showConfirm()` 函數 (Promise-based)
- [x] 3.3 將 `markPaid()` 的 confirm 改為 `await showConfirm()`
- [x] 3.4 將 `deleteStore()` 的 confirm 改為 `await showConfirm()`

## 4. 驗證

- [x] 4.1 確認所有 alert() 已移除
- [x] 4.2 確認所有 confirm() 已移除
- [ ] 4.3 測試 admin.html 所有詳情查看功能
- [ ] 4.4 測試 admin.html 所有確認對話框功能
- [ ] 4.5 測試 board.html 申請表單流程
- [ ] 4.6 測試 line-admin.html 收款確認和刪除店家功能
