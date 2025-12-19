# Tasks: add-personal-chat-features

## Implementation Tasks

### 1. 新增個人對話快捷指令處理
- [x] 在 `_handle_personal_message` 新增快捷指令檢查
- [x] 實作 `_handle_personal_quick_command` 方法
- **驗證**: 輸入「我的設定」等指令，確認正確路由

### 2. 實作查詢偏好設定功能
- [x] 新增 `_get_preferences_summary` 方法
- [x] 格式化 preferences JSONB 為可讀訊息
- **驗證**: 輸入「我的設定」，確認顯示正確偏好資訊

### 3. 實作查詢所屬群組功能
- [x] 新增 `_get_user_groups_summary` 方法
- [x] 查詢 GroupMember + Group 關聯
- [x] 只顯示 status='active' 的群組
- **驗證**: 輸入「我的群組」，確認顯示所屬群組列表

### 4. 實作查詢歷史訂單功能
- [x] 新增 `_get_order_history_summary` 方法
- [x] 查詢 Order + OrderItem 關聯，限制最近 10 筆
- [x] 格式化訂單資訊（日期、店家、品項、金額）
- **驗證**: 輸入「歷史訂單」，確認顯示訂單紀錄

### 5. 實作清除偏好設定功能
- [x] 新增 `_clear_user_preferences` 方法
- [x] 將 User.preferences 重設為空 dict
- **驗證**: 輸入「清除設定」，確認偏好被清除

### 6. 更新個人模式 AI 提示詞
- [x] 在 `_DEFAULT_PERSONAL_PROMPT` 新增查詢動作類型
- [x] 新增 `personal_query_preferences`, `personal_query_groups`, `personal_query_orders`, `personal_clear_preferences` 動作
- [x] 更新 `_execute_personal_actions` 處理新動作
- **驗證**: 用自然語言測試，如「我設定了什麼」

### 7. 更新幫助訊息
- [x] 在 `_generate_help_message` 個人模式區塊新增查詢指令說明
- **驗證**: 輸入「help」，確認顯示新指令說明

## Parallelizable Work
- Task 2-5 可並行開發（獨立功能）
- Task 6 需在 Task 2-5 完成後進行（需了解查詢方法）
- Task 7 可與其他任務並行

## Definition of Done
- [x] 所有快捷指令正常運作
- [x] AI 可透過自然語言理解查詢意圖
- [x] 訊息格式清晰易讀
- [x] 無資料遺失或安全風險
