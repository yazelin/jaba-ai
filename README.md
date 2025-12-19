# Jaba AI - LINE 群組點餐系統

呷爸 (Jaba) 是一個整合 AI 對話功能的 LINE Bot 群組點餐系統，讓群組成員可以透過自然語言進行點餐，並提供即時看板和管理後台。

> 本專案整合重寫自 [jaba](https://github.com/yazelin/jaba)（看板系統）和 [jaba-line-bot](https://github.com/yazelin/jaba-line-bot)（LINE Bot），統一為單一後端架構。

## 功能特色

### LINE Bot 點餐
- **自然語言點餐**：直接說「我要雞腿便當」即可點餐
- **跟單功能**：「+1」或「我也要」快速跟單
- **代點功能**：「幫小明點滷肉飯」代替他人點餐
- **菜單查詢**：輸入「菜單」查看今日菜單
- **訂單摘要**：「收單」時自動統計訂單

### 群組管理
- **今日店家設定**：管理員可設定當日可點餐的店家
- **管理員綁定**：使用群組代碼綁定管理員身份
- **多店家支援**：同時設定多家店家供選擇
- **群組申請審核**：透過網頁或 LINE 對話申請開通

### 個人功能
- **偏好設定**：記住使用者的飲食偏好（不吃辣、素食等）
- **歷史訂單**：查詢個人點餐紀錄
- **稱呼設定**：設定 AI 對你的稱呼

### 管理後台
- **超級管理員**：管理所有群組、店家、AI 提示詞
- **LINE 管理員**：管理群組專屬店家和菜單
- **菜單辨識**：上傳菜單圖片，AI 自動辨識品項和價格
- **即時看板**：Socket.IO 即時更新訂單狀態

### 安全特性
- **Prompt Injection 防護**：自動過濾惡意輸入
- **安全日誌**：記錄可疑行為供監控
- **LINE 簽章驗證**：確保 Webhook 請求來源

## 技術棧

| 類別 | 技術 | 版本 |
|-----|------|------|
| Web Framework | FastAPI | >=0.115.0 |
| Database | PostgreSQL + asyncpg | 16 |
| ORM | SQLAlchemy (Async) | 2.0 |
| Migration | Alembic | >=1.14.0 |
| Real-time | Socket.IO | python-socketio |
| LINE SDK | line-bot-sdk | v3 |
| AI | Claude Code CLI | Anthropic |
| Task Scheduler | APScheduler | >=3.11.1 |
| Package Manager | uv | - |
| Python | - | >=3.12 |

## 快速開始

### 1. 安裝依賴

```bash
uv sync
```

### 2. 設定環境變數

```bash
cp .env.example .env
# 編輯 .env 填入設定值
```

主要環境變數：

| 變數 | 說明 | 預設值 |
|-----|------|-------|
| `DB_HOST` | 資料庫主機 | localhost |
| `DB_PORT` | 資料庫連接埠 | 5433 |
| `DB_NAME` | 資料庫名稱 | jaba_ai |
| `DB_USER` | 資料庫使用者 | jaba_ai |
| `DB_PASSWORD` | 資料庫密碼 | - |
| `APP_PORT` | 應用程式連接埠 | 8089 |
| `INIT_ADMIN_USERNAME` | 初始管理員帳號 | admin |
| `INIT_ADMIN_PASSWORD` | 初始管理員密碼（首次啟動後無法透過 UI 修改） | - |
| `LINE_CHANNEL_SECRET` | LINE Channel Secret | - |
| `LINE_CHANNEL_ACCESS_TOKEN` | LINE Access Token | - |
| `PROJECT_ROOT` | 專案根目錄（供 Claude Code 使用） | - |

### 3. 一鍵啟動

```bash
# 啟動資料庫 + 遷移 + 應用程式
./scripts/start.sh

# 其他選項
./scripts/start.sh --db-only      # 僅啟動資料庫
./scripts/start.sh --migrate      # 僅執行遷移
./scripts/start.sh --app-only     # 僅啟動應用程式
./scripts/start.sh --stop         # 停止所有服務
```

應用程式會在 `http://localhost:8089` 啟動。

### 4. 設定 LINE Bot

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 建立 Messaging API Channel
3. 設定 Webhook URL：`https://your-domain.com/api/webhook/line`
4. 將 Channel Secret 和 Access Token 填入 `.env`

### 5. 設定 Claude Code CLI

```bash
# 安裝 Claude Code
curl -fsSL https://claude.ai/install.sh | bash

# 首次登入
claude
```

## 專案結構

```
jaba-ai/
├── app/                      # 應用程式核心
│   ├── models/               # SQLAlchemy Models (14 個模型)
│   │   ├── user.py           # 使用者
│   │   ├── group.py          # 群組、申請、成員、管理員
│   │   ├── store.py          # 店家
│   │   ├── menu.py           # 菜單、分類、品項
│   │   ├── order.py          # 訂單、Session、品項
│   │   ├── chat.py           # 對話記錄
│   │   └── system.py         # 超管、AI 提示詞、安全日誌
│   ├── repositories/         # 資料存取層 (Repository Pattern)
│   │   ├── base.py           # 基類
│   │   ├── user_repo.py      # 使用者倉儲
│   │   ├── group_repo.py     # 群組倉儲
│   │   ├── store_repo.py     # 店家倉儲
│   │   ├── order_repo.py     # 訂單倉儲
│   │   ├── chat_repo.py      # 聊天倉儲
│   │   └── system_repo.py    # 系統倉儲
│   ├── routers/              # API 路由
│   │   ├── admin.py          # 超管後台 API (/api/admin)
│   │   ├── line_admin.py     # LINE 管理員 API (/api/line-admin)
│   │   ├── line_webhook.py   # LINE Webhook (/api/webhook/line)
│   │   ├── board.py          # 看板 API (/api/board)
│   │   ├── chat.py           # 聊天 API (/api/chat)
│   │   └── public.py         # 公開 API (/api/public)
│   ├── services/             # 業務邏輯
│   │   ├── line_service.py   # LINE Bot 訊息處理 (~2,400 行)
│   │   ├── ai_service.py     # Claude Code 整合
│   │   ├── menu_service.py   # 菜單管理
│   │   ├── order_service.py  # 訂單處理
│   │   ├── cache_service.py  # 記憶體快取
│   │   └── scheduler.py      # 定時任務
│   ├── broadcast.py          # Socket.IO 事件隊列
│   ├── config.py             # 設定管理
│   └── database.py           # 資料庫連線
├── migrations/               # Alembic 遷移
│   └── versions/
│       ├── 001_initial.py
│       └── 002_seed_ai_prompts.py
├── static/                   # 前端頁面
│   ├── admin.html            # 超管後台
│   ├── line-admin.html       # LINE 管理員後台
│   ├── board.html            # 即時看板
│   ├── css/                  # 樣式
│   ├── js/                   # 前端 JavaScript
│   └── images/               # 圖片資源
├── scripts/                  # 腳本
│   ├── start.sh              # 開發用一鍵啟動
│   ├── jaba-ai.service       # systemd 服務檔案
│   ├── install-service.sh    # 安裝服務
│   └── uninstall-service.sh  # 移除服務
├── docs/                     # 詳細文件
├── openspec/                 # OpenSpec (SDD 規格驅動開發)
│   ├── AGENTS.md             # AI 協作指引
│   ├── project.md            # 專案約定與慣例
│   ├── specs/                # 系統規格（當前真實狀態的來源）
│   └── changes/              # 變更提案（spec deltas）與歷史
├── main.py                   # 應用程式入口
├── pyproject.toml            # 專案設定
├── docker-compose.yml        # Docker 設定
├── alembic.ini               # Alembic 設定
└── CLAUDE.md                 # Claude Code 專案指引
```

## 文件

| 文件 | 說明 |
|-----|------|
| [系統架構](docs/architecture.md) | 整體架構、模組說明、安全措施、技術亮點 |
| [資料庫結構](docs/database.md) | 資料表和欄位詳細說明 |
| [API 文件](docs/api.md) | RESTful API 和 Socket.IO 事件 |
| [功能清單](docs/features.md) | 各介面完整功能對照 |
| [部署說明](docs/deployment.md) | 環境設定和生產環境部署 |
| [LINE Bot 訊息流程](docs/line-bot-message-flow.md) | 訊息處理邏輯 |

## LINE Bot 指令

### 一般成員
| 指令 | 說明 |
|-----|------|
| `開單` | 開始群組點餐 |
| `收單` / `結單` | 結束點餐並顯示摘要 |
| `菜單` | 顯示今日菜單 |
| `目前訂單` | 顯示目前訂單狀況 |
| `+1` / `我也要` | 跟單（點和上一位相同的餐點） |
| `help` / `jaba` / `呷爸` | 顯示幫助訊息 |
| `id` / `群組id` | 顯示群組 ID 和用戶 ID |

### 群組管理員
| 指令 | 說明 |
|-----|------|
| `管理員 [代碼]` | 綁定管理員身份 |
| `解除管理員` | 解除管理員身份 |
| `今日` | 查看今日店家和可用店家 |
| `[店名]` | 直接輸入店名設定今日店家 |
| `加 [店名]` | 新增今日店家 |
| `移除 [店名]` | 移除今日店家 |
| `清除` | 清除所有今日店家 |

### 個人對話
| 指令 | 說明 |
|-----|------|
| `我的設定` | 查看偏好設定 |
| `我的群組` | 查看所屬群組 |
| `歷史訂單` | 查看訂單紀錄 |
| `清除設定` | 清除所有偏好 |

## 前端頁面

| 頁面 | 網址 | 說明 |
|-----|------|------|
| 看板 | `/board.html` | 即時訂單看板 + 群組申請 |
| 超管後台 | `/admin.html` | 超級管理員後台 |
| LINE 管理員 | `/line-admin.html` | LINE 群組管理員後台 |

## 開發

### 重建資料庫

```bash
uv run alembic downgrade base
uv run alembic upgrade head
```

### 查看資料庫

```bash
docker exec -it jaba-ai-postgres psql -U jaba_ai -d jaba_ai
```

### 健康檢查

```bash
curl http://localhost:8089/health
```

### 停止服務

```bash
./scripts/start.sh --stop
```

### 安裝為系統服務（生產環境）

```bash
# 安裝服務
sudo ./scripts/install-service.sh

# 啟動/停止/重啟
sudo systemctl start jaba-ai
sudo systemctl stop jaba-ai
sudo systemctl restart jaba-ai

# 查看日誌
journalctl -u jaba-ai -f

# 移除服務
sudo ./scripts/uninstall-service.sh
```

> **注意**：`main.py` 中設定了 `reload=True`，應用程式會自動監聽檔案變化並重載。生產環境如需關閉此功能，請修改 `main.py` 的 `uvicorn.run()` 設定。

### OpenSpec 規格管理

本專案使用 OpenSpec 進行規格驅動開發，透過三個斜線命令操作：

| 命令 | 說明 |
|-----|------|
| `/openspec:proposal` | 建立變更提案（proposal.md、tasks.md、spec deltas） |
| `/openspec:apply` | 實施已批准的變更，依序完成 tasks.md 中的任務 |
| `/openspec:archive` | 歸檔已部署的變更，更新 specs/ 目錄 |

```bash
# CLI 常用命令
openspec list                  # 查看進行中的變更
openspec list --specs          # 查看已部署的規格
openspec validate --all        # 驗證所有規格和變更
openspec spec view <spec-name> # 查看規格詳情
```

詳見 `openspec/AGENTS.md`。

## 架構亮點

- **完全非同步**：FastAPI + asyncio + asyncpg，支援高並發
- **Repository Pattern**：資料層與業務邏輯分離，便於測試
- **事件隊列機制**：確保 Socket.IO 通知與資料庫寫入的一致性
- **Prompt Injection 防護**：自動過濾使用者輸入中的惡意內容
- **OpenSpec 規格管理**：需求驅動開發，完整變更追蹤

## 貢獻

歡迎提交 Issue 和 Pull Request！

1. Fork 此專案
2. 建立功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交變更 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 建立 Pull Request

## 授權

本專案採用 MIT 授權條款 - 詳見 [LICENSE](LICENSE) 檔案
