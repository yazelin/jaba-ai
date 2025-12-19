# Proposal: replace-soft-delete-with-hard-delete

## Summary

將所有軟刪除（soft delete）機制改為硬刪除（hard delete），簡化程式碼並消除「查詢遺漏過濾」的問題。

## Motivation

目前系統使用軟刪除（設定 `deleted_at` 欄位）來「刪除」資料，但：

1. **查詢容易遺漏過濾** - 每個查詢都要記得加 `WHERE deleted_at IS NULL`，已發現多處遺漏
2. **沒有還原功能** - 軟刪除的主要好處（可還原）並未實作 UI
3. **增加複雜度** - 所有查詢都要額外處理刪除狀態

今天發現的問題：
- `_try_set_store_by_keyword()` 搜尋店家時沒有過濾已刪除的店家
- 導致使用者搜尋「吉」時看到 2 間店（1 間已刪除、1 間活躍）

## Scope

### 受影響的 Models（3 個）

| Model | 欄位 | 說明 |
|-------|------|------|
| User | `deleted_at` | 使用者軟刪除 |
| Group | `deleted_at` | 群組軟刪除 |
| Store | `deleted_at` | 店家軟刪除 |

### 受影響的檔案

**Models:**
- `app/models/user.py`
- `app/models/group.py`
- `app/models/store.py`

**Repositories:**
- `app/repositories/user_repo.py`
- `app/repositories/group_repo.py`
- `app/repositories/store_repo.py`

**Routers:**
- `app/routers/admin.py`
- `app/routers/line_admin.py`

**Services:**
- `app/services/line_service.py`

## Approach

1. **移除 `deleted_at` 欄位** - 從 3 個 Model 中移除
2. **改用 `session.delete()`** - 直接刪除資料
3. **移除所有 `deleted_at` 過濾** - 簡化查詢
4. **移除 `restore_group()` 方法** - 不再需要
5. **建立 Migration** - 清理已軟刪除的資料並移除欄位

## Risk Assessment

| 風險 | 影響 | 緩解措施 |
|------|------|----------|
| 資料永久刪除 | 低 | 目前沒有還原功能，行為與使用者預期一致 |
| 關聯資料 | 中 | 使用 CASCADE DELETE 或先清理關聯 |

## Success Criteria

- [ ] 所有 `deleted_at` 欄位已移除
- [ ] 刪除操作直接從資料庫移除資料
- [ ] 查詢不再需要過濾刪除狀態
- [ ] 現有功能（刪除店家、群組）正常運作
