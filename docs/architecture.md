# 呷爸 (Jaba AI) 系統架構說明

## 概述

呷爸是一個 LINE Bot 群組點餐系統，整合 AI 對話功能，讓 LINE 群組成員可以透過自然語言進行點餐，並提供即時看板和管理後台。

## 系統架構圖

```
┌─────────────────────────────────────────────────────────────────┐
│                        LINE Platform                             │
│                    (Webhook / Messaging API)                     │
└─────────────────────────────┬───────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Jaba AI Backend                             │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │                    FastAPI Application                    │   │
│  │  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐   │   │
│  │  │   Routers    │  │   Services   │  │ Repositories │   │   │
│  │  │              │  │              │  │              │   │   │
│  │  │ • webhook    │  │ • line       │  │ • user       │   │   │
│  │  │ • admin      │  │ • ai         │  │ • group      │   │   │
│  │  │ • line-admin │  │ • menu       │  │ • store      │   │   │
│  │  │ • board      │  │ • order      │  │ • order      │   │   │
│  │  │ • chat       │  │ • cache      │  │ • chat       │   │   │
│  │  │ • public     │  │ • scheduler  │  │ • system     │   │   │
│  │  └──────────────┘  └──────────────┘  └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                              │                                   │
│  ┌───────────────────────────┴───────────────────────────────┐ │
│  │                    Socket.IO Server                        │ │
│  │              (即時廣播：訂單、聊天、狀態)                   │ │
│  └───────────────────────────────────────────────────────────┘ │
└─────────────────────────────┬───────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          │                   │                   │
          ▼                   ▼                   ▼
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│   PostgreSQL    │  │  Claude Code    │  │  Static Files   │
│   (Database)    │  │   (AI Engine)   │  │  (前端頁面)      │
│                 │  │                 │  │                 │
│ • users         │  │ • 點餐對話      │  │ • board.html    │
│ • groups        │  │ • 菜單辨識      │  │ • admin.html    │
│ • stores        │  │ • 偏好設定      │  │ • line-admin    │
│ • orders        │  │                 │  │                 │
│ • ai_prompts    │  │                 │  │                 │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

## 核心模組說明

### 1. 路由層 (Routers)

| 路由 | 路徑前綴 | 說明 |
|-----|---------|------|
| `line_webhook` | `/api/webhook/line` | LINE Webhook 接收與處理 |
| `admin` | `/api/admin` | 超級管理員 API（店家、群組、訂單管理） |
| `line_admin` | `/api/line-admin` | LINE 管理員 API（群組申請、今日店家設定） |
| `board` | `/api/board` | 公開看板 API（訂單查詢） |
| `chat` | `/api/chat` | 聊天歷史 API |
| `public` | `/api/public` | 公開 API（菜單查詢、健康檢查） |

### 2. 服務層 (Services)

| 服務 | 檔案 | 說明 |
|-----|------|------|
| `LineService` | `line_service.py` | LINE Bot 訊息處理主邏輯 |
| `AiService` | `ai_service.py` | Claude Code 整合，處理對話與菜單辨識 |
| `MenuService` | `menu_service.py` | 菜單 CRUD 與圖片辨識整合 |
| `OrderService` | `order_service.py` | 訂單處理、付款狀態管理 |
| `CacheService` | `cache_service.py` | 記憶體快取（提示詞、菜單、今日店家） |
| `Scheduler` | `scheduler.py` | 定時任務（每月清理舊對話） |

### 3. 資料層 (Repositories)

採用 Repository Pattern，每個資料表對應一個 Repository：

- `UserRepository` - 使用者 CRUD
- `GroupRepository` - 群組 CRUD
- `GroupAdminRepository` - 群組管理員關聯
- `GroupMemberRepository` - 群組成員關聯
- `GroupApplicationRepository` - 群組申請審核
- `StoreRepository` - 店家 CRUD
- `MenuRepository` - 菜單 CRUD
- `OrderSessionRepository` - 點餐 Session
- `OrderRepository` - 訂單 CRUD
- `ChatRepository` - 對話記錄
- `AiPromptRepository` - AI 提示詞
- `SuperAdminRepository` - 超級管理員
- `SecurityLogRepository` - 安全日誌

### 4. 即時通訊 (Socket.IO)

透過 Socket.IO 提供即時廣播功能：

| 事件 | 說明 |
|-----|------|
| `order_update` | 訂單建立、修改、取消 |
| `chat_message` | 聊天訊息（使用者/AI） |
| `session_status` | 點餐開始/結束 |
| `payment_update` | 付款狀態變更 |
| `store_change` | 今日店家變更 |
| `application_update` | 申請狀態變更（超管房間） |
| `group_update` | 群組成員/狀態變更（超管房間） |

前端頁面透過 `join_board` 事件加入指定群組的房間，接收該群組的即時更新。

### 5. 事件隊列機制 (Event Queue)

為確保資料一致性，系統使用事件隊列機制處理 Socket.IO 廣播：

```
┌────────────────────────────────────────────────────┐
│           Request Processing Flow                   │
├────────────────────────────────────────────────────┤
│ 1. 處理業務邏輯                                      │
│ 2. 將事件加入隊列 (emit_* 函數)                      │
│ 3. 提交資料庫交易 (db.commit())                      │
│ 4. 發送所有隊列中的事件 (flush_events())             │
│ 5. 回傳回應                                          │
└────────────────────────────────────────────────────┘
```

**使用方式：**

```python
# 在 app/broadcast.py 中定義的廣播函數
await emit_order_update(group_id, data)      # 訂單更新
await emit_chat_message(group_id, data)      # 聊天訊息
await emit_session_status(group_id, data)    # 點餐狀態
await emit_payment_update(group_id, data)    # 付款更新
await emit_store_change(group_id, data)      # 店家變更
await emit_application_update(data)          # 申請更新（超管）
await emit_group_update(data)                # 群組更新（超管）

# 正確使用方式：先提交資料，再發送通知
await db.commit()
await flush_events()

# 或使用便利函數一次完成
await commit_and_notify(db)
```

**好處：**
- 確保前端收到通知時，資料庫已有最新資料
- 前端重新 fetch 時一定能取得更新後的資料
- 避免競態條件 (Race Condition)

## 群組開通與管理員綁定流程

### 群組開通流程

```
1. 邀請呷爸加入 LINE 群組
        │
        ▼
2. 群組成員輸入訊息
        │
        ▼
3. 系統自動建立 Group 記錄 (status=pending)
        │
        ▼
4. 選擇申請方式
        │
        ├─────────────────────────┬─────────────────────────┐
        │                         │                         │
        ▼                         ▼                         │
   【LINE 群組對話申請】      【網頁申請】                  │
   呷爸使用 AI 引導          前往 /board.html              │
   (group_intro prompt)      填寫申請表單                  │
        │                         │                         │
        │  收集資料：             │                         │
        │  • 群組名稱             │                         │
        │  • 聯絡方式             │                         │
        │  • 群組代碼             │                         │
        │                         │                         │
        └─────────────────────────┴─────────────────────────┘
                                  │
                                  ▼
5. 系統建立 GroupApplication 記錄 (status=pending)
                                  │
                                  ▼
6. 超級管理員在後台審核申請
        │
        ├─ 拒絕：更新 application.status=rejected
        │
        └─ 通過：
            ├─ 更新 application.status=approved
            ├─ 更新 group.status=active
            └─ 複製 group_code 到 Group 記錄

⚠️ 審核結果不會主動推送 LINE 通知
   群組成員下次發訊息時才會發現狀態變更
```

### 管理員綁定流程

群組開通後，需要有管理員才能設定今日店家。管理員綁定方式：

```
1. 群組成員在群組中輸入「管理員 [群組代碼]」
        │
        ▼
2. 系統驗證：
   ├─ 群組是否已啟用 (status=active)
   └─ 群組代碼是否正確 (group.group_code)
        │
        ▼
3. 驗證通過：
   ├─ 建立 GroupAdmin 記錄
   └─ 回應「✅ 已綁定為管理員」

4. 驗證失敗：
   └─ 回應「⚠️ 代碼錯誤」
```

**重要說明：**
- 群組代碼由申請者在申請時自訂
- 群組代碼同時用於：管理員綁定、LINE 管理員後台登入
- 群組代碼可在 LINE 管理員後台變更
- 一個群組代碼可能關聯多個群組（同公司不同群組使用相同代碼）

---

## 訊息處理流程

### LINE 群組訊息流程

```
訊息進入
    │
    ├─ 特殊指令 (help, id) → 直接回應
    │
    ├─ 群組未啟用 → 引導申請
    │
    ├─ 記錄成員
    │
    ├─ 快捷指令 (開單、收單、菜單) → 直接處理
    │
    ├─ 管理員指令 (今日店家設定) → 權限檢查後處理
    │
    └─ AI 對話 → Claude Code 處理點餐
```

### LINE 個人訊息流程

```
訊息進入
    │
    ├─ 特殊指令 (help, id) → 直接回應
    │
    ├─ 非群組成員 → 引導加入群組
    │
    ├─ 快捷指令 (我的設定、歷史訂單) → 直接處理
    │
    └─ AI 對話 → Claude Code 處理偏好設定
```

## AI 整合架構

### Claude Code 調用方式

```python
# 對話模式 (使用 haiku 模型)
claude -p --model haiku --system-prompt "..." "訊息內容"

# 菜單辨識模式 (使用 opus 模型)
claude -p --model opus --tools Read --allowedTools Read "請辨識菜單..."
```

### AI 提示詞管理

提示詞存儲於 `ai_prompts` 表，透過 Alembic Migration 初始化：

| 名稱 | 用途 |
|-----|------|
| `group_ordering` | 群組點餐對話（active 群組） |
| `group_intro` | 群組申請引導（pending 群組） |
| `personal_preferences` | 個人偏好設定對話 |
| `manager_prompt` | 超管後台 AI 對話 |
| `menu_recognition` | 菜單圖片辨識 |

### AI Context 組成

AI 對話時會傳入三個部分：系統上下文 (context)、對話歷史 (history)、當前訊息。

#### 1. 系統上下文 (Context)

根據不同模式，context 結構不同：

**群組點餐模式** (`group_ordering` / `group_idle`)：
```json
{
  "mode": "group_ordering",    // 或 "group_idle"（未開單）
  "user_name": "林亞澤",        // 當前發言者名稱
  "today_stores": [            // 今日店家列表
    {"id": "uuid", "name": "好吃便當"}
  ],
  "menus": [                   // 店家菜單（含分類、品項、價格、變體）
    {
      "store_id": "uuid",
      "store_name": "好吃便當",
      "categories": [
        {
          "name": "便當類",
          "items": [
            {"name": "雞腿便當", "price": 85, "variants": [], "is_available": true}
          ]
        }
      ]
    }
  ],
  "session_orders": [          // 本次點餐的所有訂單（含其他人的）
    {
      "user_name": "小明",
      "items": [{"name": "雞腿便當", "quantity": 1, "note": "不要辣"}],
      "total": 85
    }
  ],
  "user_preferences": {        // 當前使用者的個人偏好
    "preferred_name": "小澤",
    "dietary_restrictions": ["不吃辣"]
  }
}
```

**個人偏好模式** (`personal_preferences`)：
```json
{
  "mode": "personal_preferences",
  "user_name": "林亞澤",
  "user_preferences": {
    "preferred_name": "小澤",
    "dietary_restrictions": ["不吃辣", "素食"],
    "taste_preferences": ["清淡"]
  }
}
```

**群組申請模式** (`group_application`)：
```json
{
  "mode": "group_application",
  "user_name": "林亞澤"
}
```

#### 2. 對話歷史 (History)

由 `CHAT_HISTORY_LIMIT` 環境變數控制（預設 40 則）：

```
林亞澤: 魚
助手: 菜單中有魚排飯 $100，要這個嗎？
林亞澤: 對
助手: 好～幫你點一個魚排飯 $100！
阿花: +1
助手: 好～幫阿花點一個魚排飯！
```

#### 3. 完整訊息結構

```
[系統上下文]
{context JSON}

[對話歷史]
{formatted history}

[當前訊息]
林亞澤: 我要改成雞腿飯

請以 JSON 格式回應：
{"message": "你的回應訊息", "actions": [{"type": "動作類型", "data": {...}}]}
```

#### 4. AI 回應格式

AI 回應需包含 `message` 和 `actions`：

```json
{
  "message": "好～幫你改成雞腿便當 $85！",
  "actions": [
    {
      "type": "group_update_order",
      "data": {
        "old_item": "魚排飯",
        "new_item": {
          "name": "雞腿便當",
          "quantity": 1,
          "note": ""
        }
      }
    }
  ]
}
```

**群組點餐 action types：**
- `group_create_order` - 建立訂單品項
- `group_update_order` - 修改訂單品項（替換）
- `group_remove_item` - 移除品項
- `group_cancel_order` - 取消整筆訂單

**個人模式 action types：**
- `update_user_profile` - 更新使用者偏好設定
- `personal_query_preferences` - 查詢偏好設定
- `personal_query_groups` - 查詢所屬群組
- `personal_query_orders` - 查詢歷史訂單

**群組申請 action types：**
- `submit_application` - 提交群組申請

**重點：**
- 對話歷史會顯示每位使用者的名稱，讓 AI 能區分多人對話
- `session_orders` 包含所有人的訂單，讓 AI 能處理「跟單」和「幫 XXX 點」
- 歷史長度建議：5 人 × 4 輪對話 = 40 則

---

## 安全措施

### Prompt Injection 防護

系統在所有使用者輸入傳送給 AI 之前，會經過 `sanitize_user_input()` 函數過濾，防止惡意注入攻擊：

| 過濾項目 | 說明 |
|---------|------|
| XML/HTML 標籤 | 移除 `<tag>` 形式的標籤 |
| Markdown Code Blocks | 移除 ` ``` ` 包裹的程式碼區塊 |
| 連續分隔線 | 移除 `---` 或 `===` 等分隔符號 |
| 長度限制 | 單則訊息最多 200 字元 |

### 安全日誌記錄

當輸入觸發過濾規則時，系統會記錄到 `security_logs` 表：

```
SecurityLog:
  - line_user_id: 發送者 ID
  - original_message: 原始訊息
  - sanitized_message: 過濾後訊息
  - trigger_reasons: 觸發原因 ["xml_tags", "code_blocks", ...]
  - context_type: group / personal
```

### 其他安全機制

| 機制 | 說明 |
|-----|------|
| LINE 簽章驗證 | Webhook 驗證 X-Line-Signature |
| 使用者封鎖 | 支援 `is_banned` 欄位封鎖惡意用戶 |
| 密碼雜湊 | 超管密碼使用雜湊存儲（目前為 SHA-256，如需更高安全性可升級為 bcrypt） |

## 權限架構

### 三層權限模型

```
超級管理員 (Super Admin)
    │
    ├─ 管理所有群組
    ├─ 管理全局店家 (scope=global)
    ├─ 審核群組申請
    └─ 管理 AI 提示詞

LINE 群組管理員 (Group Admin)
    │
    ├─ 管理群組今日店家
    ├─ 管理群組專屬店家 (scope=group)
    ├─ 查看群組訂單
    └─ 標記付款狀態

一般成員 (Member)
    │
    ├─ 點餐
    ├─ 查看菜單
    ├─ 設定個人偏好
    └─ 查看歷史訂單
```

### 店家權限範圍 (Scope)

| Scope | 說明 | 可見群組 | 可編輯者 |
|-------|------|---------|---------|
| `global` | 全局店家 | 所有群組 | 超級管理員 |
| `group` | 群組專屬店家 | 指定 group_code 的群組 | 該群組管理員 |

## 技術棧

| 層級 | 技術 |
|-----|------|
| Web Framework | FastAPI |
| Database | PostgreSQL 16 + asyncpg |
| ORM | SQLAlchemy 2.0 (Async) |
| Migration | Alembic |
| Real-time | Socket.IO (python-socketio) |
| LINE SDK | line-bot-sdk v3 |
| AI | Claude Code CLI (Anthropic) |
| Task Scheduler | APScheduler |
| Package Manager | uv |

## 目錄結構

```
jaba-ai/
├── app/
│   ├── __init__.py
│   ├── config.py           # 設定管理
│   ├── database.py         # 資料庫連線
│   ├── broadcast.py        # Socket.IO 廣播
│   ├── models/             # SQLAlchemy Models
│   │   ├── user.py
│   │   ├── group.py
│   │   ├── store.py
│   │   ├── menu.py
│   │   ├── order.py
│   │   ├── chat.py
│   │   └── system.py
│   ├── repositories/       # 資料存取層
│   ├── routers/            # API 路由
│   └── services/           # 業務邏輯
├── migrations/             # Alembic 遷移
│   └── versions/
│       ├── 001_initial.py
│       └── 002_seed_ai_prompts.py
├── static/                 # 前端頁面
│   ├── board.html          # 即時看板
│   ├── admin.html          # 超管後台
│   └── line-admin.html     # LINE 管理員後台
├── docs/                   # 文件
├── openspec/               # OpenSpec 規格管理
│   ├── AGENTS.md          # AI 代理程式使用說明
│   ├── project.md         # 專案約定
│   ├── specs/             # 已部署規格
│   └── changes/           # 變更提案與歷史
├── scripts/                # 啟動腳本
│   └── start.sh           # 一鍵啟動
├── main.py                 # 應用程式入口
├── pyproject.toml          # 專案設定
└── docker-compose.yml      # Docker 設定
```

## 應用程式生命週期

### 啟動流程

應用程式啟動時會依序執行：

1. **註冊廣播函數** - 將 Socket.IO 廣播函數註冊到事件系統
2. **初始化超級管理員** - 檢查並建立初始超管帳號（首次啟動）
3. **啟動定時任務排程器** - 啟動背景任務（如每月清理舊對話）

```python
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 啟動
    register_broadcasters(...)
    await _init_super_admin()
    start_scheduler()

    yield  # 應用程式運行期間

    # 關閉
    stop_scheduler()
```

### 定時任務

| 任務 | 排程 | 說明 |
|-----|------|------|
| 清理舊對話 | 每月 1 日 00:00 | 刪除 6 個月前的聊天記錄 |

## 技術亮點與設計決策

### 完全非同步架構

- **技術選擇**：FastAPI + asyncio + asyncpg
- **為什麼選擇非同步？**
  - **I/O 密集型應用**：LINE Bot 主要時間花在等待外部服務（LINE API、資料庫查詢、AI 回應），非同步可在等待時處理其他請求
  - **自然的並發模型**：一個請求等待 AI 回應時（約 2-5 秒），伺服器仍可處理其他群組的訊息
  - **資源效率**：相比多執行緒方案，非同步使用更少記憶體，且不需要處理鎖和競爭條件
- **同步 vs 非同步差異**：同步架構需要每個請求獨佔一個執行緒等待，非同步架構可在等待期間釋放控制權處理其他任務

### Repository Pattern

- **優勢**：資料層與業務邏輯分離
- **便於測試**：可輕鬆替換資料來源進行單元測試
- **查詢集中**：SQL 查詢邏輯集中管理，便於優化

### 事件隊列機制

- **解決問題**：避免 Socket.IO 通知與資料庫寫入的競態條件
- **實現方式**：先將事件加入隊列，等資料庫提交後再批次發送

### OpenSpec (SDD 規格驅動開發)

- **核心理念**：在寫程式碼前，人類與 AI 先對「要做什麼」達成共識
- **specs/ 目錄**：系統規格的唯一真實來源（source of truth），描述當前系統狀態
- **changes/ 目錄**：變更提案（spec deltas），只包含差異而非完整規格
- **三階段工作流程**：`/openspec:proposal`（草擬）→ `/openspec:apply`（實施）→ `/openspec:archive`（歸檔）
- **優勢**：AI 只需處理隔離的 spec deltas，而非整個程式碼庫，提升 token 效率

### 記憶體快取

- **實現**：使用 Python dict 作為快取
- **適用場景**：中小型應用
- **擴展**：生產環境可升級為 Redis
