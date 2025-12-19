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
- **Web 框架**: FastAPI
- **即時通訊**: Socket.IO
- **AI**: Claude Code (CLI)
- **LINE SDK**: line-bot-sdk >= 3.0.0
- **ASGI 伺服器**: Uvicorn
- **資料庫**: PostgreSQL + asyncpg (Docker)
- **資料庫遷移**: Alembic
- **ORM**: SQLAlchemy 2.0 (async)
- **反向代理**: nginx (Docker)
- **部署**: 內網伺服器

## Project Conventions

### Code Style
- 繁體中文註解和文件
- PEP 8 程式碼風格
- snake_case 函數命名
- PascalCase 類別命名

### Architecture Patterns
- **模組化設計**: 功能分離到 `app/` 目錄
- **事件驅動**: Socket.IO 廣播即時更新
- **Repository 模式**: 資料存取層抽象化
- **非同步優先**: async/await 處理 I/O

### Database Design
- UUID 作為主鍵
- created_at / updated_at 時間戳
- 軟刪除使用 deleted_at
- JSONB 儲存彈性結構資料
- 群組為核心組織單位

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
