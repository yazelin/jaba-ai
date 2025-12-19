# 實作任務清單

## 階段一：後端 API

### 1.1 使用者管理 API
- [x] `GET /api/admin/users` - 使用者列表
  - 分頁參數：`limit`, `offset`
  - 搜尋參數：`search`（名稱或 LINE ID）
  - 篩選參數：`status`（all/active/banned）
  - 回傳：使用者列表含統計資訊
- [x] `GET /api/admin/users/{user_id}` - 使用者詳情
  - 回傳：完整使用者資訊、所屬群組、最近訂單
- [x] `POST /api/admin/users/{user_id}/ban` - 封鎖使用者
  - 設定 `is_banned=True`, `banned_at=now()`
- [x] `POST /api/admin/users/{user_id}/unban` - 解除封鎖
  - 設定 `is_banned=False`, `banned_at=None`

### 1.2 群組管理 API 擴展
- [x] `GET /api/admin/groups` 增強
  - 新增分頁、搜尋、篩選支援
  - 回傳成員數、管理員數統計
- [x] `GET /api/admin/groups/{group_id}/members` - 群組成員列表
- [x] `PUT /api/admin/groups/{group_id}` - 更新群組資訊
- [x] `POST /api/admin/groups/{group_id}/suspend` - 停用群組
- [x] `POST /api/admin/groups/{group_id}/activate` - 啟用群組

### 1.3 Repository 擴展
- [x] `UserRepository` 新增方法
  - `get_all_paginated()` - 分頁列表
  - `search_by_name_or_id()` - 搜尋
  - `get_with_stats()` - 含統計資訊
  - `ban_user()` - 封鎖
  - `unban_user()` - 解封
- [x] `GroupRepository` 新增方法
  - `get_all_paginated()` - 分頁列表
  - `get_with_stats()` - 含成員數統計
  - `suspend_group()` - 停用
  - `activate_group()` - 啟用

## 階段二：前端重構

### 2.1 標籤頁導航
- [x] 建立標籤頁 HTML 結構
- [x] 實作標籤切換 JavaScript
- [x] 各標籤頁內容容器
- [x] 標籤頁樣式（CSS）

### 2.2 AI 懸浮對話框
- [x] 懸浮按鈕 HTML/CSS
  - 右下角固定定位
  - 圓形按鈕含 Jaba 圖示
  - hover/active 狀態
- [x] 對話框容器
  - 標題列（標題 + 最小化/關閉按鈕）
  - 對話訊息區域
  - 輸入區域
- [x] 展開/收合動畫
- [x] 狀態管理（localStorage 記住偏好）
- [x] 遷移現有對話功能

### 2.3 現有功能遷移
- [x] 店家管理 → 店家管理標籤
- [x] 群組選擇器 + 訂單 → 獨立區域
- [x] 群組申請審核 → 群組管理標籤
- [x] AI 提示詞 + 系統維護 → 系統設定標籤

## 階段三：新功能 UI

### 3.1 違規記錄面板
- [x] 統計卡片區
  - 今日違規數
  - 本週違規數
  - 總違規數
- [x] 違規列表表格
  - 欄位：時間、使用者、群組、訊息、原因、操作
  - 點擊展開詳情
- [x] 篩選器
  - 日期範圍選擇
  - 群組下拉選單
- [x] 分頁控制
- [x] 「封鎖使用者」按鈕（連結到使用者管理）

### 3.2 使用者管理面板
- [x] 搜尋框
- [x] 狀態篩選下拉選單
- [x] 使用者列表表格
  - 欄位：頭像、名稱、LINE ID、群組數、訂單數、狀態、操作
  - 狀態標籤樣式（正常=綠、封鎖=紅）
- [x] 分頁控制
- [x] 封鎖/解封確認對話框
- [x] 使用者詳情 Modal
  - 基本資訊
  - 所屬群組列表
  - 最近訂單
  - 違規記錄

### 3.3 群組管理面板增強
- [x] 搜尋框
- [x] 狀態篩選
- [x] 群組列表表格
  - 欄位：名稱、LINE ID、代碼、狀態、成員數、管理員數、建立時間、操作
- [x] 分頁控制
- [x] 編輯群組 Modal
- [x] 停用/啟用確認對話框
- [x] 群組成員 Modal
  - 成員列表
  - 管理員標記
- [x] 整合現有審核功能

## 階段四：測試與調整

### 4.1 功能測試
- [x] 使用者管理 CRUD
- [x] 群組管理 CRUD
- [x] 違規記錄檢視
- [x] 懸浮對話框互動
- [x] 標籤頁切換

### 4.2 RWD 調整
- [x] 平板 (<1024px) 佈局
- [x] 手機 (<768px) 佈局
- [x] 懸浮對話框響應式

### 4.3 效能優化
- [x] 列表虛擬捲動（大量資料時）
- [x] 圖片懶載入
- [x] API 回應快取

## 檔案變更清單

### 新增檔案
- `static/js/admin-tabs.js` - 標籤頁管理
- `static/js/admin-chat-widget.js` - 懸浮對話框
- `static/js/admin-users.js` - 使用者管理
- `static/js/admin-groups.js` - 群組管理
- `static/js/admin-security.js` - 違規記錄

### 修改檔案
- `static/admin.html` - 主要介面重構
- `static/css/style.css` - 新增樣式
- `app/routers/admin.py` - 新增 API 端點
- `app/repositories/user_repo.py` - 新增方法
- `app/repositories/group_repo.py` - 新增方法
