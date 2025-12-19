# Tasks: add-hybrid-store-menu-management

## Task List

### Phase 1: 資料庫變更

- [x] **1.1** 新增 Store 欄位 migration
  - 新增 `scope` 欄位 (String, default='global')
  - 新增 `group_code` 欄位 (String, nullable)
  - 新增 `created_by_type` 欄位 (String, default='admin')
  - 建立索引
  - 現有資料設為 global
  - **驗證**: `uv run alembic upgrade head` 成功 ✓

- [x] **1.2** 更新 Store model
  - 新增三個欄位的型別定義
  - **驗證**: Model 與 migration 一致 ✓

### Phase 2: Repository 層

- [x] **2.1** 擴充 StoreRepository
  - `get_stores_for_group_code(group_code)` - 取得群組可用店家
  - `get_stores_by_scope(scope, group_code=None)` - 依 scope 篩選
  - `can_edit_store(store, group_code)` - 權限檢查
  - **驗證**: 單元測試 ✓

### Phase 3: 菜單差異比對

- [x] **3.1** 移植 `compare_menus` 函式
  - 從 jaba/app/ai.py 移植到 menu_service.py
  - 調整為 async 版本
  - **驗證**: 對比結果正確 ✓

- [x] **3.2** 新增差異儲存 API
  - `POST /api/admin/stores/{id}/menu/save` 支援 `diff_mode`
  - 實作 `apply_items` 和 `remove_items` 邏輯
  - **驗證**: curl 測試差異儲存 ✓

### Phase 4: 超管後台 API 擴充

- [x] **4.1** 擴充超管店家 API
  - 新增店家時可指定 `scope`
  - 列表支援 `scope` 篩選參數
  - **驗證**: curl 測試 ✓

- [x] **4.2** 新增菜單差異比對 API
  - `GET /api/admin/stores/{id}/menu/compare` - 取得差異預覽
  - **驗證**: 上傳菜單後能看到差異 ✓

### Phase 5: LINE 管理員店家 API

- [x] **5.1** 新增 LINE 管店家 CRUD API
  - `GET /api/line-admin/stores/by-code/{group_code}` - 列表（自動依 group_code 篩選）
  - `POST /api/line-admin/stores/by-code/{group_code}` - 新增（自動設 scope=group）
  - `PUT /api/line-admin/stores/by-code/{group_code}/{id}` - 編輯（權限檢查）
  - `DELETE /api/line-admin/stores/by-code/{group_code}/{id}` - 刪除（權限檢查）
  - **驗證**: curl 測試 CRUD ✓

- [x] **5.2** 新增 LINE 管菜單 API
  - `GET /api/line-admin/stores/by-code/{group_code}/{id}/menu` - 取得菜單
  - `POST /api/line-admin/stores/by-code/{group_code}/{id}/menu/recognize` - 上傳/辨識菜單
  - `POST /api/line-admin/stores/by-code/{group_code}/{id}/menu` - 儲存菜單
  - `POST /api/line-admin/stores/by-code/{group_code}/{id}/menu/save` - 儲存（支援 diff_mode）
  - `GET /api/line-admin/stores/by-code/{group_code}/{id}/menu/compare` - 差異比對
  - **驗證**: curl 測試 ✓

### Phase 6: 前端 UI

- [x] **6.1** LINE 管理員頁面 - 店家管理
  - 店家列表（區分全局/群組，can_edit 標記）
  - 新增店家 Modal
  - 編輯/刪除店家 Modal
  - **驗證**: 瀏覽器測試 ✓

- [x] **6.2** LINE 管理員頁面 - 菜單管理
  - 點擊店家顯示菜單
  - 上傳菜單圖片辨識
  - **驗證**: 瀏覽器測試 ✓

- [x] **6.3** 差異預覽 UI
  - 新增/修改/刪除三區塊
  - checkbox 選擇套用項目
  - 套用選取項目按鈕
  - **驗證**: 上傳菜單後能預覽差異 ✓

- [x] **6.4** 超管後台 - 差異預覽整合
  - 整合差異預覽 UI 到 admin.html (已存在)
  - **驗證**: 瀏覽器測試 ✓

### Phase 7: AI Prompt 調整

- [x] **7.1** 調整店家資訊注入
  - 修改 `_get_stores_for_group` 區分全局/群組
  - 修改 `_find_store_by_name` 限群組可用範圍
  - 修改 `_get_available_stores_hint` 顯示群組可用店家
  - 修改 `_get_today_stores_summary` 顯示群組可用店家
  - **驗證**: 查看 AI 收到的 prompt ✓

### Phase 8: 整合測試

- [x] **8.1** 權限測試
  - LINE 管無法編輯全局店家 ✓
  - LINE 管只能編輯相同 group_code 的店家 ✓
  - 超管可編輯所有店家 ✓
  - **驗證**: 多種情境測試 ✓

- [x] **8.2** 端對端測試
  - LINE 管新增店家 → 上傳菜單 → 差異預覽 → 套用 ✓
  - 驗證 API 正確返回結果 ✓
  - **驗證**: 完整流程無錯誤 ✓

## Dependencies
- Phase 2 depends on Phase 1
- Phase 3-5 depends on Phase 2
- Phase 6 depends on Phase 3-5
- Phase 7 depends on Phase 5
- Phase 8 depends on all

## Notes
- `compare_menus` 函式從舊專案 `~/SDD/jaba/app/ai.py` 移植
- 差異預覽 UI 參考舊專案設計
- 權限檢查統一在 API 層處理
