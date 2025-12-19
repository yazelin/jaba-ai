# Proposal: fix-broadcast-race-condition

## Summary
修正 Socket.IO 廣播與資料庫 commit 之間的 race condition，確保前端收到通知後 fetch 的資料一定是最新的。

## Problem Statement
目前系統的流程：
1. Service 更新資料
2. Service 呼叫 `emit_*` 發送 Socket 通知
3. Router 呼叫 `db.commit()` 提交資料

這導致 **race condition**：
- 前端在步驟 2 收到通知
- 前端立即發起 API fetch 新資料
- 但 Router 還沒執行步驟 3 的 commit
- 前端取得的是舊資料

此外，部分 Router 漏掉 `await db.commit()`，導致：
- 資料沒有持久化
- Socket 通知發送了但資料實際上沒有更新

## Proposed Solution
1. **Event Queue 機制**：`emit_*` 函數將事件加入 request-scoped 隊列，不立即發送
2. **commit_and_notify(db) helper**：統一執行 `db.commit()` + `flush_events()`
3. **更新所有使用點**：將 `await db.commit()` 改為 `await commit_and_notify(db)`

這確保：
- 事件一定在 commit 之後才發送
- 不會遺漏 commit
- 不會遺漏 flush events
- 前端收到通知時資料已經是最新的

## Scope
- `app/broadcast.py` - 新增 Event Queue 機制
- `app/routers/admin.py` - 更新 commit 呼叫
- `app/routers/line_admin.py` - 更新 commit 呼叫
- `app/routers/chat.py` - 更新 commit 呼叫
- `app/services/line_service.py` - emit 呼叫不需改動（自動變成 queue）
- `app/services/order_service.py` - emit 呼叫不需改動（自動變成 queue）

## Non-Goals
- 不改變 Socket.IO 事件的格式或內容
- 不改變前端的處理邏輯
- 不處理 LINE Webhook 的流程（那是獨立的 transaction 邊界）

## Risks & Mitigations
| Risk | Mitigation |
|------|------------|
| 遺漏更新某個 commit 呼叫 | 全面搜尋並建立完整任務清單 |
| ContextVar 在某些情況下行為不如預期 | 使用標準的 contextvars 模組，這是 Python 推薦的 request-scoped 狀態管理方式 |
| 事件在 commit 失敗時仍被保留 | 在 try-except 中確保失敗時清空隊列 |

## Success Criteria
- [ ] 前端收到 Socket 通知後 fetch 的資料一定是最新的
- [ ] 所有需要 commit 的 endpoint 都使用 `commit_and_notify(db)`
- [ ] 無新增的 race condition
