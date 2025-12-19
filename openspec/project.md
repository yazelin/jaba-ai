# Project Context

## Purpose
呷爸 AI (jaba-ai) 是一個整合式的 LINE 群組點餐系統，結合 AI 對話能力、看板顯示、管理員後台於單一應用程式。

本專案整合自兩個既有專案：
- **jaba** (`~/SDD/jaba`)：提供看板功能、管理員後台、AI 對話處理、菜單辨識
- **jaba-line-bot** (`~/SDD/jaba-line-bot`)：提供 LINE Webhook 處理、群組點餐 Session、個人化設定

整合目標：
1. 單一應用部署，減少維運複雜度
2. JSON 檔案遷移至 PostgreSQL 資料庫
3. 新增群組申請審核機制
4. 新增 LINE 管理員認證機制（以群組為單位的權限控制）
5. 讓管理員可透過 LINE 執行後台管理功能
6. 今日菜單以群組為單位
7. 保留原有的看板和管理員後台 UI

## Tech Stack
- **語言**: Python 3.12+
- **套件管理**: uv
- **Web 框架**: FastAPI >= 0.115.0
- **ASGI 伺服器**: Uvicorn
- **資料庫**: PostgreSQL 16 (Docker)
- **ORM**: SQLAlchemy 2.0 (async)
- **連線驅動**: asyncpg
- **資料庫遷移**: Alembic
- **即時通訊**: python-socketio
- **LINE SDK**: line-bot-sdk v3
- **AI**: Claude Code (CLI)
- **HTTP Client**: httpx
- **排程**: APScheduler
- **部署**: systemd + Docker Compose

## Project Conventions

### Code Style
- 繁體中文註解和文件
- PEP 8 程式碼風格
- snake_case 函數命名
- PascalCase 類別命名

### Architecture Patterns
- **分層架構**: Routers → Services → Repositories → Models
- **Repository Pattern**: 資料層與業務邏輯分離，查詢邏輯集中管理
- **完全非同步**: FastAPI + asyncio + asyncpg，適合 I/O 密集型應用
- **事件隊列機制**: 先將事件加入隊列，資料庫提交後批次發送，避免競態條件
- **即時廣播**: Socket.IO 廣播訂單、聊天、點餐狀態、店家變更事件

### Database Design
- UUID 作為主鍵
- created_at / updated_at 時間戳
- 軟刪除使用 deleted_at
- JSONB 儲存彈性結構資料
- 群組為核心組織單位

### Security
- **Prompt Injection 防護**: `sanitize_user_input()` 過濾惡意輸入
- **LINE 簽章驗證**: Webhook 驗證 X-Line-Signature
- **安全日誌**: 記錄可疑輸入到 `security_logs` 表

## Domain Context

### 核心實體
- **群組 (Group)**: LINE 群組，系統核心組織單位
- **使用者 (User)**: LINE 使用者
- **店家 (Store)**: 餐點商家（全域共用）
- **群組今日店家 (GroupTodayStore)**: 群組的今日店家
- **點餐 Session (OrderSession)**: 群組的點餐活動
- **訂單 (Order)**: 使用者的訂餐記錄

### 共享店家模式
- 所有群組共用店家資料
- 每個群組設定自己的「今日店家」

### 群組生命週期
1. 申請：後台填寫申請表單
2. 審核：超級管理員審核
3. 啟用：審核通過
4. 使用：群組成員點餐

### 權限模型
- **超級管理員**: 後台管理、審核申請、管理店家、指定群組管理員
- **群組管理員**: LINE 內管理群組（今日店家、菜單、訂單）
- **一般使用者**: 點餐、設定個人偏好

## External Dependencies
- **LINE Messaging API**: 訊息收發
- **Claude**: AI 對話處理
- **PostgreSQL**: 資料庫 (Docker container)
- **nginx**: 反向代理 (Docker container)
