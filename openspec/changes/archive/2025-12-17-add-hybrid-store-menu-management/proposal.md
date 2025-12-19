# Proposal: add-hybrid-store-menu-management

## Summary
實作混合式店家/菜單管理架構，讓超級管理員和 LINE 管理員都能新增店家與菜單，並建立兩層級權限機制確保資料安全。

## Why
目前店家和菜單只能由超級管理員在後台建立，LINE 管理員無法自主新增常用的店家，導致：
1. LINE 管理員需要依賴超管才能新增店家
2. 不同群組可能有各自常用的店家，難以自主管理
3. 缺乏菜單差異比對功能，每次上傳會完全覆蓋

## What Changes

### 1. 店家分層架構
- **全局店家 (scope=global)**：超管建立，所有群組可用，LINE 管不可編輯
- **群組店家 (scope=group)**：LINE 管建立，只有相同群組代碼的群組可用

### 2. 權限規則
- LINE 管只能編輯自己建立的店家（scope=group 且 group_code 匹配）
- LINE 管不能覆蓋或修改超管建立的全局店家
- 超管可以編輯所有店家

### 3. 菜單差異更新
- 上傳新菜單時顯示差異預覽（新增/修改/刪除）
- 支援選擇性更新（不完全覆蓋）
- 從舊專案 (jaba) 移植 `compare_menus` 功能

### 4. AI Prompt 調整
- 注入店家資訊時區分全局/群組店家
- 優先顯示群組專屬店家，再顯示全局店家

## Affected Components
- `app/models/store.py` - 新增 scope, group_code 欄位
- `app/routers/admin.py` - 超管店家 API
- `app/routers/line_admin.py` - LINE 管店家 API
- `app/services/menu_service.py` - 菜單差異比對
- `app/services/ai_service.py` - Prompt 注入調整
- `static/line-admin.html` - 店家管理 UI
- `static/admin.html` - 差異預覽 UI
- `migrations/` - 新增欄位 migration

## Out of Scope
- 複雜促銷組合（滿額折扣、跨品項組合）
- 促銷有效期限管理
- 店家合併功能（將群組店家升級為全局店家）

## Risks and Mitigations
| 風險 | 緩解措施 |
|-----|---------|
| LINE 管建立重複店家 | 建立時提示相似店家名稱 |
| 菜單差異比對不準確 | 使用模糊比對（去除空白、標點） |
| 權限判斷錯誤導致資料外洩 | API 層統一檢查 scope 和 group_code |
