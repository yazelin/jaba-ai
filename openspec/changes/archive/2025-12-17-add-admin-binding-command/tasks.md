# Tasks: add-admin-binding-command

## Implementation Tasks

### 1. 新增 GroupApplicationRepository 查詢方法
- [x] 新增 `get_approved_by_line_group_id(line_group_id)` 方法
- [x] 回傳該群組已核准的申請（用於取得 admin_password）
- **驗證**: 可查詢到已核准申請的密碼

### 2. 實作管理員綁定指令
- [x] 在 `_handle_admin_command` 中加入「管理員 XXX」指令處理
- [x] 新增 `_bind_admin` 方法
- [x] 查詢 group_applications 驗證密碼
- [x] 驗證成功後呼叫 `admin_repo.add_admin()`
- **驗證**: 輸入正確密碼成功綁定

### 3. 處理各種情況
- [x] 密碼正確：綁定成功並提示可用指令
- [x] 密碼錯誤：提示「密碼錯誤」
- [x] 已是管理員：提示「您已經是管理員」
- [x] 找不到申請：提示「密碼錯誤」（不透露申請不存在）
- **驗證**: 各情況回應正確

### 4. 更新申請頁面說明
- [x] 修改 `line-admin.html` 的管理密碼說明
- [x] 補充：「也可在群組中輸入『管理員 [密碼]』綁定管理員身份」
- **驗證**: 申請頁面顯示新說明

## Definition of Done
- [x] 管理員可透過密碼綁定真實 LINE 帳號
- [x] 綁定後可使用所有管理員指令
- [x] 密碼錯誤時不透露多餘資訊
- [x] 申請頁面說明已更新
