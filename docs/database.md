# 資料庫結構說明

## 概述

Jaba AI 使用 PostgreSQL 16 作為主要資料庫，透過 SQLAlchemy 2.0 (Async) 進行 ORM 操作，使用 Alembic 管理資料庫遷移。

## ER Diagram

```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     users       │     │     groups      │     │     stores      │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ line_user_id    │◄────│ activated_by    │     │ name            │
│ display_name    │     │ line_group_id   │     │ scope           │
│ picture_url     │     │ name            │     │ group_code      │
│ preferences     │     │ group_code      │     │ is_active       │
│ is_banned       │     │ status          │     └────────┬────────┘
└────────┬────────┘     └────────┬────────┘
         │                       │                       │
         │  ┌────────────────────┼───────────────────────┘
         │  │                    │
         ▼  ▼                    ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ group_members   │     │  group_admins   │     │ group_today_    │
├─────────────────┤     ├─────────────────┤     │    stores       │
│ id (PK)         │     │ id (PK)         │     ├─────────────────┤
│ group_id (FK)   │     │ group_id (FK)   │     │ id (PK)         │
│ user_id (FK)    │     │ user_id (FK)    │     │ group_id (FK)   │
│ joined_at       │     │ granted_by (FK) │     │ store_id (FK)   │
└─────────────────┘     └─────────────────┘     │ date            │
                                                └─────────────────┘
         │
         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ order_sessions  │     │     orders      │     │   order_items   │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │◄────│ session_id (FK) │◄────│ order_id (FK)   │
│ group_id (FK)   │     │ id (PK)         │     │ id (PK)         │
│ status          │     │ user_id (FK)    │     │ menu_item_id    │
│ started_by (FK) │     │ store_id (FK)   │     │ name            │
│ ended_by (FK)   │     │ total_amount    │     │ quantity        │
└─────────────────┘     │ payment_status  │     │ unit_price      │
                        └─────────────────┘     │ subtotal        │
                                                └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│     menus       │     │ menu_categories │     │   menu_items    │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │◄────│ menu_id (FK)    │◄────│ category_id(FK) │
│ store_id (FK)   │     │ id (PK)         │     │ id (PK)         │
└─────────────────┘     │ name            │     │ name            │
                        │ sort_order      │     │ price           │
                        └─────────────────┘     │ variants        │
                                                └─────────────────┘

┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   ai_prompts    │     │  super_admins   │     │  security_logs  │
├─────────────────┤     ├─────────────────┤     ├─────────────────┤
│ id (PK)         │     │ id (PK)         │     │ id (PK)         │
│ name            │     │ username        │     │ line_user_id    │
│ content         │     │ password_hash   │     │ line_group_id   │
└─────────────────┘     └─────────────────┘     │ original_message│
                                                │ trigger_reasons │
                                                └─────────────────┘
```

**資料表總計：17 張**

## 資料表詳細說明

### users - 使用者

儲存 LINE 使用者資訊和個人偏好設定。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| line_user_id | VARCHAR(64) | LINE 用戶 ID（唯一） |
| display_name | VARCHAR(128) | LINE 顯示名稱 |
| picture_url | TEXT | LINE 頭像網址 |
| preferences | JSONB | 個人偏好設定 |
| is_banned | BOOLEAN | 是否被封鎖（預設 false） |
| banned_at | TIMESTAMP | 封鎖時間 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**preferences 範例：**
```json
{
  "preferred_name": "小明",
  "dietary_restrictions": ["不吃辣", "素食"],
  "taste_preferences": ["清淡", "少油"]
}
```

---

### groups - LINE 群組

儲存 LINE 群組資訊和啟用狀態。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| line_group_id | VARCHAR(64) | LINE 群組 ID（唯一） |
| name | VARCHAR(256) | 群組名稱 |
| description | TEXT | 群組描述 |
| group_code | VARCHAR(64) | 群組代碼（管理員登入/綁定用） |
| status | VARCHAR(32) | 狀態：pending/active/suspended |
| activated_at | TIMESTAMP | 啟用時間 |
| activated_by | UUID (FK) | 啟用者 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引：** `line_group_id`, `group_code`

---

### group_applications - 群組申請

儲存群組開通申請記錄。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| line_group_id | VARCHAR(64) | LINE 群組 ID |
| group_name | VARCHAR(256) | 申請的群組名稱 |
| contact_info | TEXT | 聯絡資訊 |
| group_code | VARCHAR(64) | 群組代碼（管理員登入用） |
| status | VARCHAR(32) | 狀態：pending/approved/rejected |
| reviewed_at | TIMESTAMP | 審核時間 |
| reviewed_by | UUID (FK) | 審核者 |
| review_note | TEXT | 審核備註 |
| created_at | TIMESTAMP | 申請時間 |
| updated_at | TIMESTAMP | 更新時間 |

---

### group_members - 群組成員

記錄使用者與群組的成員關係。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| group_id | UUID (FK) | 群組 ID |
| user_id | UUID (FK) | 使用者 ID |
| joined_at | TIMESTAMP | 加入時間 |

**唯一約束：** `(group_id, user_id)`

---

### group_admins - 群組管理員

記錄群組管理員權限。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| group_id | UUID (FK) | 群組 ID |
| user_id | UUID (FK) | 使用者 ID |
| granted_by | UUID (FK) | 授權者 |
| granted_at | TIMESTAMP | 授權時間 |

**唯一約束：** `(group_id, user_id)`

---

### stores - 店家

儲存店家資訊，支援全局和群組專屬兩種範圍。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| name | VARCHAR(256) | 店家名稱 |
| phone | VARCHAR(32) | 電話 |
| address | TEXT | 地址 |
| description | TEXT | 描述 |
| note | TEXT | 備註 |
| is_active | BOOLEAN | 是否啟用 |
| scope | VARCHAR(16) | 範圍：global/group |
| group_code | VARCHAR(64) | 群組代碼（scope=group 時使用） |
| created_by_type | VARCHAR(16) | 建立者類型：admin/line_admin |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引：** `scope`, `group_code`, `is_active`

---

### menus - 菜單

儲存店家菜單，與店家一對一關係。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| store_id | UUID (FK) | 店家 ID（唯一） |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

---

### menu_categories - 菜單分類

儲存菜單的分類項目。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| menu_id | UUID (FK) | 菜單 ID |
| name | VARCHAR(128) | 分類名稱 |
| sort_order | INTEGER | 排序順序 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

---

### menu_items - 菜單品項

儲存菜單的餐點品項。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| category_id | UUID (FK) | 分類 ID |
| name | VARCHAR(256) | 品項名稱 |
| price | NUMERIC(10,2) | 價格 |
| description | TEXT | 描述 |
| variants | JSONB | 尺寸變體 |
| promo | JSONB | 促銷資訊 |
| is_available | BOOLEAN | 是否供應 |
| sort_order | INTEGER | 排序順序 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**variants 範例：**
```json
[
  {"name": "M", "price": 35},
  {"name": "L", "price": 40}
]
```

**promo 範例：**
```json
{
  "type": "buy_one_get_one",
  "label": "買一送一"
}
```

---

### group_today_stores - 今日店家

記錄每個群組每天的店家設定。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| group_id | UUID (FK) | 群組 ID |
| store_id | UUID (FK) | 店家 ID |
| date | DATE | 日期 |
| set_by | UUID (FK) | 設定者 |
| set_at | TIMESTAMP | 設定時間 |

**唯一約束：** `(group_id, store_id, date)`

---

### order_sessions - 點餐 Session

記錄每次群組點餐的開始和結束。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| group_id | UUID (FK) | 群組 ID |
| status | VARCHAR(32) | 狀態：ordering/ended |
| started_at | TIMESTAMP | 開始時間 |
| started_by | UUID (FK) | 開單者 |
| ended_at | TIMESTAMP | 結束時間 |
| ended_by | UUID (FK) | 收單者 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引：** `group_id`

---

### orders - 訂單

記錄使用者在每次點餐中的訂單。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| session_id | UUID (FK) | Session ID |
| user_id | UUID (FK) | 使用者 ID |
| store_id | UUID (FK) | 店家 ID |
| total_amount | NUMERIC(10,2) | 訂單總金額 |
| payment_status | VARCHAR(32) | 付款狀態：unpaid/paid/refunded |
| paid_amount | NUMERIC(10,2) | 已付金額 |
| paid_at | TIMESTAMP | 付款時間 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引：** `session_id`, `user_id`

---

### order_items - 訂單品項

記錄訂單中的各個品項。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| order_id | UUID (FK) | 訂單 ID |
| menu_item_id | UUID (FK) | 菜單品項 ID（可為 null） |
| name | VARCHAR(256) | 品項名稱 |
| quantity | INTEGER | 數量 |
| unit_price | NUMERIC(10,2) | 單價 |
| subtotal | NUMERIC(10,2) | 小計 |
| options | JSONB | 客製化選項 |
| note | TEXT | 備註 |
| created_at | TIMESTAMP | 建立時間 |

**options 範例：**
```json
{
  "size": "L",
  "sugar": "微糖",
  "ice": "去冰"
}
```

---

### chat_messages - 聊天記錄

儲存群組和個人的對話歷史。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| group_id | UUID (FK) | 群組 ID（個人對話為 null） |
| user_id | UUID (FK) | 使用者 ID |
| session_id | UUID (FK) | Session ID（可為 null） |
| role | VARCHAR(20) | 角色：user/assistant/system |
| content | TEXT | 訊息內容 |
| created_at | TIMESTAMP | 建立時間 |

**索引：** `group_id`, `user_id`, `created_at`

---

### ai_prompts - AI 提示詞

儲存 AI 對話的系統提示詞。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| name | VARCHAR(128) | 提示詞名稱（唯一） |
| content | TEXT | 提示詞內容 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**預設提示詞：**
- `group_ordering` - 群組點餐對話
- `personal_preferences` - 個人偏好設定對話
- `manager_prompt` - 超管後台 AI 對話
- `group_intro` - 群組申請引導（pending 群組）
- `menu_recognition` - 菜單圖片辨識

---

### super_admins - 超級管理員

儲存超級管理員帳號。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| username | VARCHAR(64) | 帳號（唯一） |
| password_hash | VARCHAR(256) | 密碼雜湊 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

---

### security_logs - 安全日誌

記錄可疑輸入，用於監控和防護 Prompt Injection 攻擊。

| 欄位 | 類型 | 說明 |
|-----|------|------|
| id | UUID | 主鍵 |
| line_user_id | VARCHAR(64) | LINE 用戶 ID |
| display_name | VARCHAR(128) | 用戶顯示名稱 |
| line_group_id | VARCHAR(64) | LINE 群組 ID（個人對話為 null） |
| original_message | TEXT | 原始訊息內容 |
| sanitized_message | TEXT | 過濾後的訊息內容 |
| trigger_reasons | JSONB | 觸發原因列表 |
| context_type | VARCHAR(16) | 對話類型：group/personal |
| created_at | TIMESTAMP | 記錄時間 |

**索引：** `line_user_id`, `line_group_id`, `created_at`

**trigger_reasons 範例：**
```json
["xml_tags_removed", "length_truncated", "code_blocks_removed"]
```

## 遷移管理

### 執行遷移

```bash
# 升級到最新版本
uv run alembic upgrade head

# 降級一個版本
uv run alembic downgrade -1

# 查看目前版本
uv run alembic current
```

### 遷移檔案

| 版本 | 檔案 | 說明 |
|-----|------|------|
| 001 | `001_initial.py` | 建立所有資料表 |
| 002 | `002_seed_ai_prompts.py` | 初始化 AI 提示詞 |

## 資料庫連線設定

環境變數：
```
DB_HOST=localhost
DB_PORT=5433
DB_NAME=jaba_ai
DB_USER=jaba_ai
DB_PASSWORD=your_password
```

連線字串格式：
```
postgresql+asyncpg://{user}:{password}@{host}:{port}/{database}
```
