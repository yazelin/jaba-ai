# Change: 超管後台功能增強

## Why
目前超管後台存在以下限制：
1. **缺少違規記錄檢視** - 後端 API 已實作 (`/api/admin/security-logs`)，但沒有 UI 顯示
2. **缺少使用者管理** - 無法查看使用者列表、封鎖狀態、解除封鎖
3. **缺少群組管理** - 除審核外，無法檢視/編輯/停用現有群組
4. **對話框佔用空間** - 目前 AI 助手對話框位於畫面中央，壓縮了其他功能的展示空間

## What Changes
- 新增標籤頁導航：[店家管理] [群組管理] [使用者管理] [違規記錄] [系統設定]
- 將 AI 助手對話框改為右下角懸浮式設計（類似 Messenger/Intercom）
- 新增使用者管理 API 和 UI（列表、搜尋、封鎖/解封）
- 擴展群組管理 API 和 UI（分頁、搜尋、停用/啟用、成員查看）
- 新增違規記錄檢視面板（統計卡片、列表、篩選）

## Impact
- Affected specs: `line-admin`
- Affected code:
  - `app/routers/admin.py` - 新增 API 端點
  - `app/repositories/user_repo.py` - 新增方法
  - `app/repositories/group_repo.py` - 新增方法
  - `static/admin.html` - 主要介面重構
  - `static/css/style.css` - 新增樣式
  - `static/js/` - 新增多個 JS 模組
