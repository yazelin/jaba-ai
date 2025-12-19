# Tasks: add-group-admin-store-commands

## Implementation Tasks

### 1. 新增群組管理員指令檢查
- [x] 在 `_handle_group_message` 中加入管理員指令檢查（在快捷指令之前）
- [x] 實作 `_handle_admin_command` 方法
- [x] 檢查使用者是否為群組管理員
- **驗證**: 非管理員執行指令無回應

### 2. 實作查詢今日店家功能
- [x] 新增 `_get_today_stores_summary` 方法
- [x] 快捷指令：「今日店家」
- **驗證**: 輸入「今日店家」顯示目前設定

### 3. 實作設定今日店家功能
- [x] 新增 `_set_today_store` 方法
- [x] 快捷指令：「設定店家 XXX」
- [x] 從 `stores` 表查詢已存在的店家
- [x] 模糊匹配店名（名稱包含輸入內容）
- [x] 找不到時提示「找不到店家」並列出可用店家
- [x] 清除原有店家後設定新店家
- **驗證**: 輸入「設定店家 XXX」正確設定；輸入不存在店名提示可用店家

### 4. 實作新增今日店家功能
- [x] 新增 `_add_today_store` 方法
- [x] 快捷指令：「加店家 XXX」
- [x] 從 `stores` 表查詢並模糊匹配
- **驗證**: 輸入「加店家 XXX」新增一家

### 5. 實作移除今日店家功能
- [x] 新增 `_remove_today_store` 方法
- [x] 快捷指令：「移除店家 XXX」
- [x] 從今日店家中匹配店名
- **驗證**: 輸入「移除店家 XXX」移除特定店家

### 6. 實作清除今日店家功能
- [x] 新增 `_clear_today_stores` 方法
- [x] 快捷指令：「清除店家」
- **驗證**: 輸入「清除店家」清除所有

### 7. 更新回應判斷邏輯
- [x] 在 `_handle_group_message` 中管理員指令處理在 `_should_respond_in_group` 之前
- [x] 非點餐中時，管理員指令也應回應
- **驗證**: 非點餐狀態下管理員指令有回應

### 8. 清除快取
- [x] 操作後清除 `CacheService.clear_today_stores()`
- **驗證**: 看板即時更新

## Parallelizable Work
- Task 2-6 可並行開發（獨立功能）
- Task 7 需在指令實作後進行

## Definition of Done
- [x] 所有快捷指令正常運作
- [x] 權限檢查正確（僅管理員可操作）
- [x] 操作後快取正確清除
- [x] 看板即時更新今日店家
