# Tasks: simplify-application-form

## Task List

### Phase 1: 前端申請表單更新

- [x] **1.1** 更新 `line-admin.html` 申請表單
  - 將「管理密碼」改為「群組代碼」
  - 合併「申請人姓名」和「聯絡方式」為「聯絡資訊」單一欄位
  - 移除「申請原因」欄位
  - 更新說明文字：清楚說明群組代碼的用途與非保密性質
  - **驗證**: ✅ 瀏覽器開啟申請頁面，確認欄位正確顯示

- [x] **1.2** 更新 `line-admin.html` 變更密碼面板
  - 將「變更密碼」改為「變更群組代碼」
  - 更新相關提示文字
  - **驗證**: ✅ 登入後確認面板文字正確

### Phase 2: 後端 API 更新

- [x] **2.1** 更新 `line_admin.py` API 模型
  - 修改 `GroupApplicationCreate` 模型
    - 移除 `applicant_name`, `applicant_contact` 欄位
    - 新增 `contact_info` 欄位
    - 將 `password` 欄位改名為 `group_code`（API 層面）
  - 更新 `create_application` 處理邏輯
  - **驗證**: ✅ 使用 curl 測試申請 API

- [x] **2.2** 更新 `line_admin.py` 變更代碼 API
  - 將 `ChangePassword` 改為 `ChangeGroupCode`
  - 更新錯誤訊息文字（密碼錯誤 → 代碼錯誤）
  - **驗證**: ✅ 使用 curl 測試變更代碼 API

### Phase 3: LINE 指令文字更新

- [x] **3.1** 更新 `line_service.py` 管理員指令說明
  - 將「管理員 [密碼]」改為「管理員 [代碼]」
  - 更新 `_bind_admin` 方法的回應文字
  - 更新 `_unbind_admin` 方法的回應文字
  - 更新管理員指令幫助訊息
  - **驗證**: ✅ 透過測試腳本驗證指令回應

### Phase 4: 規格文件更新

- [x] **4.1** 更新 `openspec/specs/line-bot/spec.md`
  - 修改 Admin Binding Command 中的「密碼」為「代碼」
  - 更新 Application Page Description requirement
  - **驗證**: ✅ 規格文件已更新

### Phase 5: 整合測試

- [x] **5.1** 端對端測試
  - 測試完整申請流程（新簡化欄位）
  - 測試群組代碼變更功能
  - 測試 LINE 群組內綁定管理員指令
  - 測試管理後台登入（使用群組代碼）
  - **驗證**: ✅ 全流程無錯誤

### Phase 6: 資料庫簡化（額外）

- [x] **6.1** 簡化資料庫 schema
  - 更新 `001_initial.py` migration
    - `users` 表移除 `line_admin_password`, `line_admin_password_created_at`
    - `group_applications` 表移除 `applicant_name`, `applicant_contact`, `reason`
    - `group_applications` 表新增 `contact_info`，`admin_password` 改名為 `group_code`
  - 刪除 `003_add_admin_password_to_group_applications.py`（整合至 001）
  - 更新 `app/models/group.py` 和 `app/models/user.py`
  - 更新 `app/routers/admin.py` 和 `static/admin.html` 對應欄位
  - **驗證**: ✅ 重建資料庫並測試所有功能

## Dependencies
- Task 2.1 depends on Task 1.1 (前端欄位與 API 需同步)
- Task 5.1 depends on all previous tasks
- Task 6.1 由用戶要求額外執行（不需向下相容）

## Notes
- ~~資料庫欄位 `admin_password` 保持不變，僅 UI/API 層面更名~~
- ~~既有申請資料中的 `applicant_name` 和 `applicant_contact` 仍保留在資料庫中~~
- **已更新**: 資料庫欄位已完全簡化，`admin_password` 改名為 `group_code`，移除未使用欄位
