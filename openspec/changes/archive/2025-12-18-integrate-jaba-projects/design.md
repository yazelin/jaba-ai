# Technical Design: 整合 jaba 專案

## Context
整合 jaba 和 jaba-line-bot 兩個專案，從 JSON 檔案存儲遷移到 PostgreSQL 資料庫，新增群組申請審核和 LINE 管理員功能。

## Goals / Non-Goals

### Goals
- 單一應用程式部署
- PostgreSQL 資料庫存儲
- 群組為核心的資料組織
- LINE 管理員功能
- 保留既有 UI 和功能

### Non-Goals
- 多租戶 SaaS 架構
- 多 AI Provider 支援
- 雲端部署

## Database Schema

### Entity Relationship Diagram

```
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   users     │───┬───│ group_members   │───┬───│   groups    │
└─────────────┘   │   └─────────────────┘   │   └─────────────┘
                  │                         │         │
                  │   ┌─────────────────┐   │         │
                  └───│ group_admins    │───┘         │
                      └─────────────────┘             │
                                                      │
┌─────────────┐       ┌─────────────────┐             │
│   stores    │───────│ group_today_    │─────────────┘
└─────────────┘       │ stores          │
      │               └─────────────────┘
      │
┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   menus     │───────│ menu_categories │───────│ menu_items  │
└─────────────┘       └─────────────────┘       └─────────────┘

┌─────────────┐       ┌─────────────────┐       ┌─────────────┐
│   groups    │───────│ order_sessions  │───────│   orders    │
└─────────────┘       └─────────────────┘       └─────────────┘
                                                      │
                                                ┌─────────────┐
                                                │ order_items │
                                                └─────────────┘

┌─────────────┐
│ group_      │
│ applications│
└─────────────┘
```

### Tables Definition

#### users - 使用者
```sql
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_user_id VARCHAR(64) UNIQUE NOT NULL,
    display_name VARCHAR(128),
    picture_url TEXT,

    -- 個人偏好 (JSONB)
    preferences JSONB DEFAULT '{}'::jsonb,
    -- {
    --   "preferred_name": "小明",
    --   "dietary_restrictions": ["不吃辣"],
    --   "allergies": ["海鮮"],
    --   "drink_preferences": ["無糖", "去冰"],
    --   "notes": ""
    -- }

    is_super_admin BOOLEAN DEFAULT FALSE,

    -- LINE 管理員簡易後台密碼（一人一密碼）
    line_admin_password VARCHAR(64),
    line_admin_password_created_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_users_line_user_id ON users(line_user_id);
```

#### groups - LINE 群組
```sql
CREATE TABLE groups (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_group_id VARCHAR(64) UNIQUE NOT NULL,
    name VARCHAR(256),
    description TEXT,

    status VARCHAR(32) DEFAULT 'pending',
    -- pending: 待審核
    -- active: 已啟用
    -- suspended: 已停用

    activated_at TIMESTAMPTZ,
    activated_by UUID REFERENCES users(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_groups_line_group_id ON groups(line_group_id);
CREATE INDEX idx_groups_status ON groups(status);
```

#### group_applications - 群組申請
```sql
CREATE TABLE group_applications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    line_group_id VARCHAR(64) NOT NULL,
    group_name VARCHAR(256),
    applicant_name VARCHAR(128),
    applicant_contact TEXT,
    reason TEXT,

    status VARCHAR(32) DEFAULT 'pending',
    -- pending: 待審核
    -- approved: 已通過
    -- rejected: 已拒絕

    reviewed_at TIMESTAMPTZ,
    reviewed_by UUID REFERENCES users(id),
    review_note TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_group_applications_status ON group_applications(status);
```

#### group_members - 群組成員
```sql
CREATE TABLE group_members (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    joined_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(group_id, user_id)
);

CREATE INDEX idx_group_members_group ON group_members(group_id);
CREATE INDEX idx_group_members_user ON group_members(user_id);
```

#### group_admins - 群組管理員
```sql
CREATE TABLE group_admins (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,

    granted_at TIMESTAMPTZ DEFAULT NOW(),
    granted_by UUID REFERENCES users(id),

    UNIQUE(group_id, user_id)
);

CREATE INDEX idx_group_admins_group ON group_admins(group_id);
CREATE INDEX idx_group_admins_user ON group_admins(user_id);
```

#### stores - 店家
```sql
CREATE TABLE stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(256) NOT NULL,
    phone VARCHAR(32),
    address TEXT,
    description TEXT,
    note TEXT,

    is_active BOOLEAN DEFAULT TRUE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW(),
    deleted_at TIMESTAMPTZ
);

CREATE INDEX idx_stores_is_active ON stores(is_active) WHERE deleted_at IS NULL;
```

#### menus - 菜單
```sql
CREATE TABLE menus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menus_store ON menus(store_id);
```

#### menu_categories - 菜單分類
```sql
CREATE TABLE menu_categories (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    menu_id UUID NOT NULL REFERENCES menus(id) ON DELETE CASCADE,
    name VARCHAR(128) NOT NULL,
    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menu_categories_menu ON menu_categories(menu_id);
```

#### menu_items - 菜單品項
```sql
CREATE TABLE menu_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    category_id UUID NOT NULL REFERENCES menu_categories(id) ON DELETE CASCADE,
    name VARCHAR(256) NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,

    is_available BOOLEAN DEFAULT TRUE,

    -- 尺寸變體 (JSONB)
    variants JSONB DEFAULT '[]'::jsonb,
    -- [{"name": "M", "price": 35}, {"name": "L", "price": 40}]

    -- 促銷資訊 (JSONB)
    promo JSONB,
    -- {"type": "discount", "label": "買一送一", "value": 50}

    sort_order INTEGER DEFAULT 0,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_menu_items_category ON menu_items(category_id);
CREATE INDEX idx_menu_items_available ON menu_items(is_available);
```

#### group_today_stores - 群組今日店家
```sql
CREATE TABLE group_today_stores (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,
    store_id UUID NOT NULL REFERENCES stores(id) ON DELETE CASCADE,
    date DATE NOT NULL DEFAULT CURRENT_DATE,

    set_by UUID REFERENCES users(id),
    set_at TIMESTAMPTZ DEFAULT NOW(),

    UNIQUE(group_id, store_id, date)
);

CREATE INDEX idx_group_today_stores_group_date ON group_today_stores(group_id, date);
```

#### order_sessions - 點餐 Session
```sql
CREATE TABLE order_sessions (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id UUID NOT NULL REFERENCES groups(id) ON DELETE CASCADE,

    status VARCHAR(32) DEFAULT 'ordering',
    -- ordering: 點餐中
    -- ended: 已結束

    started_at TIMESTAMPTZ DEFAULT NOW(),
    started_by UUID REFERENCES users(id),
    ended_at TIMESTAMPTZ,
    ended_by UUID REFERENCES users(id),

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_order_sessions_group ON order_sessions(group_id);
CREATE INDEX idx_order_sessions_status ON order_sessions(status);
```

#### orders - 訂單
```sql
CREATE TABLE orders (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id UUID NOT NULL REFERENCES order_sessions(id) ON DELETE CASCADE,
    user_id UUID NOT NULL REFERENCES users(id),
    store_id UUID NOT NULL REFERENCES stores(id),

    total_amount DECIMAL(10, 2) DEFAULT 0,

    -- 付款狀態
    payment_status VARCHAR(32) DEFAULT 'unpaid',
    -- unpaid: 未付款
    -- paid: 已付款
    -- refunded: 已退款

    paid_amount DECIMAL(10, 2) DEFAULT 0,
    paid_at TIMESTAMPTZ,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_orders_session ON orders(session_id);
CREATE INDEX idx_orders_user ON orders(user_id);
```

#### order_items - 訂單品項
```sql
CREATE TABLE order_items (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    order_id UUID NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
    menu_item_id UUID REFERENCES menu_items(id),

    name VARCHAR(256) NOT NULL,
    quantity INTEGER DEFAULT 1,
    unit_price DECIMAL(10, 2) NOT NULL,
    subtotal DECIMAL(10, 2) NOT NULL,

    -- 客製化選項 (JSONB)
    options JSONB DEFAULT '{}'::jsonb,
    -- {"size": "L", "sugar": "微糖", "ice": "去冰"}

    note TEXT,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_order_items_order ON order_items(order_id);
```

#### chat_messages - 對話記錄
```sql
CREATE TABLE chat_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),

    -- 可以是群組對話或個人對話
    group_id UUID REFERENCES groups(id) ON DELETE CASCADE,
    user_id UUID REFERENCES users(id),

    role VARCHAR(32) NOT NULL,  -- user, assistant
    content TEXT NOT NULL,

    -- 關聯的 session (如果是點餐對話)
    session_id UUID REFERENCES order_sessions(id) ON DELETE SET NULL,

    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_chat_messages_group ON chat_messages(group_id, created_at DESC);
CREATE INDEX idx_chat_messages_user ON chat_messages(user_id, created_at DESC);
CREATE INDEX idx_chat_messages_session ON chat_messages(session_id);
```

#### system_config - 系統設定
```sql
CREATE TABLE system_config (
    key VARCHAR(128) PRIMARY KEY,
    value JSONB NOT NULL,
    updated_at TIMESTAMPTZ DEFAULT NOW()
);

-- 預設值
INSERT INTO system_config (key, value) VALUES
    ('admin_password', '"9898"'),
    ('server_port', '8089');
```

#### ai_prompts - AI 提示詞
```sql
CREATE TABLE ai_prompts (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(128) UNIQUE NOT NULL,
    -- group_ordering, manager, personal, menu_recognition

    content TEXT NOT NULL,

    created_at TIMESTAMPTZ DEFAULT NOW(),
    updated_at TIMESTAMPTZ DEFAULT NOW()
);
```

## Application Architecture

### Directory Structure
```
jaba-ai/
├── main.py                      # FastAPI 應用入口
├── app/
│   ├── __init__.py
│   ├── config.py                # 設定管理
│   ├── database.py              # 資料庫連線
│   ├── models/                  # SQLAlchemy Models
│   │   ├── __init__.py
│   │   ├── user.py
│   │   ├── group.py
│   │   ├── store.py
│   │   ├── menu.py
│   │   ├── order.py
│   │   └── chat.py
│   ├── repositories/            # 資料存取層
│   │   ├── __init__.py
│   │   ├── user_repo.py
│   │   ├── group_repo.py
│   │   ├── store_repo.py
│   │   └── order_repo.py
│   ├── services/                # 業務邏輯
│   │   ├── __init__.py
│   │   ├── ai_service.py
│   │   ├── order_service.py
│   │   └── line_service.py
│   ├── routers/                 # API 路由
│   │   ├── __init__.py
│   │   ├── public.py            # 公開 API
│   │   ├── admin.py             # 管理員 API
│   │   ├── line_webhook.py      # LINE Webhook
│   │   └── board.py             # 看板 API
│   └── utils/                   # 工具函數
│       ├── __init__.py
│       └── helpers.py
├── templates/                   # HTML 模板
│   ├── index.html               # 看板
│   └── manager.html             # 管理後台
├── static/                      # 靜態資源
├── migrations/                  # Alembic 遷移
│   ├── versions/
│   └── env.py
├── alembic.ini
├── pyproject.toml
├── docker-compose.yml
└── .env
```

### Docker Compose
```yaml
version: '3.8'

services:
  postgres:
    image: postgres:16-alpine
    environment:
      POSTGRES_DB: jaba
      POSTGRES_USER: jaba
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf:ro
      - ./certs:/etc/nginx/certs:ro
    depends_on:
      - app

  app:
    build: .
    environment:
      DATABASE_URL: postgresql+asyncpg://jaba:${DB_PASSWORD}@postgres:5432/jaba
      LINE_CHANNEL_SECRET: ${LINE_CHANNEL_SECRET}
      LINE_CHANNEL_ACCESS_TOKEN: ${LINE_CHANNEL_ACCESS_TOKEN}
    depends_on:
      - postgres

volumes:
  postgres_data:
```

## Decisions

### 1. 使用 PostgreSQL 而非繼續使用 JSON 檔案
- **決定**: 遷移到 PostgreSQL
- **原因**: 支援複雜查詢、關聯、事務、併發
- **替代方案**: SQLite（不支援併發）、保留 JSON（查詢困難）

### 2. 使用 SQLAlchemy 2.0 async
- **決定**: 使用 SQLAlchemy 2.0 搭配 asyncpg
- **原因**: 與 FastAPI 非同步架構整合、型別安全、ORM 便利性
- **替代方案**: 純 asyncpg（失去 ORM 便利）、SQLModel（較新不穩定）

### 3. 群組為核心組織單位
- **決定**: 大部分資料以群組為核心組織
- **原因**: 符合業務邏輯（每個群組有自己的今日店家、訂單 session）
- **替代方案**: 扁平結構（查詢複雜）

### 4. 店家全域共用
- **決定**: 店家資料全域共用，群組只設定「今日店家」
- **原因**: 減少重複資料，便於管理
- **替代方案**: 每群組複製店家資料（維護困難）

### 5. 整合 LINE Webhook 到主應用
- **決定**: LINE Webhook 處理整合到 FastAPI 應用
- **原因**: 單一部署，減少網路延遲
- **替代方案**: 保持分離（維運複雜）

## Risks / Trade-offs

### Risk 1: 資料遷移複雜度
- **風險**: 既有 JSON 資料遷移可能遺漏或錯誤
- **緩解**: 建立完整遷移腳本，保留原資料備份

### Risk 2: 學習曲線
- **風險**: SQLAlchemy 2.0 async 學習曲線
- **緩解**: 從簡單模型開始，漸進式開發

### Risk 3: 效能變化
- **風險**: 資料庫查詢效能與 JSON 讀取不同
- **緩解**: 適當建立索引，必要時使用快取

## Migration Plan

### Phase 1: 基礎設施
1. 建立 Docker Compose 環境
2. 設定 PostgreSQL
3. 建立 Alembic 遷移
4. 建立基本 Models

### Phase 2: 核心功能
1. 實作 Repository 層
2. 實作店家管理
3. 實作群組管理
4. 整合 LINE Webhook

### Phase 3: 點餐功能
1. 實作點餐 Session
2. 實作訂單管理
3. 整合 AI 對話

### Phase 4: 管理功能
1. 實作群組申請審核
2. 實作 LINE 管理員功能
3. 實作後台管理介面

### Phase 5: 遷移
1. 建立資料遷移腳本
2. 測試遷移
3. 正式遷移

## Confirmed Decisions

| 項目 | 決定 |
|------|------|
| AI Provider | 僅支援 Claude |
| LINE Channel | 使用原有 jaba-line-bot 的 Channel |
| 數據遷移 | 不需要，從零開始 |
| LINE 管理員登入 | 超級管理員產生密碼（一人一密碼，存在 users 表）|
| 看板權限 | 完全公開 |
| 圖片儲存 | 檔案系統 (static/images/)，菜單辨識圖片不儲存 |
| 歷史訂單 | 需要，可查詢跨天記錄 |
| AI 提示詞編輯 | 需要後台介面 |
| 快取策略 | 記憶體 dict + 更新時主動清除 |
| 日誌 | API 請求日誌 + Webhook 處理時間記錄 |
| 圖片壓縮 | 上傳時壓縮（不影響 AI 辨識前提下）|

## Performance & Monitoring

### In-Memory Cache
使用 Python dict 實作簡單的記憶體快取，更新資料時主動清除快取：

```python
# 快取（普通 dict）
menu_cache = {}
today_stores_cache = {}
prompt_cache = {}

# 查詢時：有快取就用
async def get_menu(store_id: str):
    if store_id in menu_cache:
        return menu_cache[store_id]
    menu = await db.query(...)
    menu_cache[store_id] = menu
    return menu

# 更新時：清除快取
async def update_menu(store_id: str, data):
    await db.update(...)
    menu_cache.pop(store_id, None)  # 清掉快取
```

快取項目：
- 店家菜單（更新菜單時清除）
- 今日店家（設定今日店家時清除）
- AI 提示詞（編輯提示詞時清除）

### Request Logging
```python
import logging
import time

logger = logging.getLogger("jaba")

@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    duration = time.time() - start

    logger.info(f"{request.method} {request.url.path} - {response.status_code} - {duration:.3f}s")
    return response
```

### Webhook Timing
```python
@router.post("/callback")
async def line_webhook(request: Request):
    start = time.time()

    # ... 處理邏輯 ...

    duration = time.time() - start
    logger.info(f"Webhook processed in {duration:.3f}s")
    return {"status": "ok"}
```

### Image Compression
菜單辨識時壓縮圖片（不儲存，僅用於 AI 辨識）：

```python
from PIL import Image
import io

def compress_for_recognition(image_bytes: bytes, max_size: int = 1920) -> bytes:
    """壓縮圖片用於 AI 辨識，不影響辨識品質"""
    img = Image.open(io.BytesIO(image_bytes))

    # 保持比例縮放
    if max(img.size) > max_size:
        ratio = max_size / max(img.size)
        new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
        img = img.resize(new_size, Image.Resampling.LANCZOS)

    # 轉為 JPEG 壓縮（品質 85 通常足夠 AI 辨識）
    output = io.BytesIO()
    img.save(output, format='JPEG', quality=85)
    return output.getvalue()
```

## Open Questions

（已全部解決）
