## 1. Models 修改

- [x] 1.1 從 `User` model 移除 `deleted_at` 欄位
- [x] 1.2 從 `Group` model 移除 `deleted_at` 欄位
- [x] 1.3 從 `Store` model 移除 `deleted_at` 欄位

## 2. Repositories 修改

- [x] 2.1 `user_repo.py` - 移除所有 `deleted_at` 過濾條件
- [x] 2.2 `group_repo.py` - 移除 `deleted_at` 過濾，刪除 `soft_delete_group()` 和 `restore_group()` 方法，改用硬刪除
- [x] 2.3 `store_repo.py` - 移除所有 `deleted_at` 過濾條件

## 3. Routers 修改

- [x] 3.1 `admin.py` - 店家刪除改為 `db.delete(store)`
- [x] 3.2 `line_admin.py` - 店家刪除改為 `db.delete(store)`，移除 `deleted_at` 檢查

## 4. Services 修改

- [x] 4.1 `line_service.py` - 移除 `_try_set_store_by_keyword()` 中的 `deleted_at` 過濾

## 5. Database Migration

- [x] 5.1 建立 migration：清理已軟刪除的資料（deleted_at IS NOT NULL）
- [x] 5.2 建立 migration：移除 `deleted_at` 欄位
- [x] 5.3 執行 migration

## 6. 驗證

- [x] 6.1 確認資料庫欄位已移除
- [x] 6.2 確認軟刪除資料已清理（「炭吉」店家從 2 間變 1 間）
- [x] 6.3 測試店家刪除功能（admin.html）
- [x] 6.4 測試店家刪除功能（line-admin.html）
