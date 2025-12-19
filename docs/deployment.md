# 部署與設定說明

## 系統需求

- Python 3.12+
- PostgreSQL 16+
- Claude Code CLI（安裝方式見下方說明）

## 快速開始

### 1. 安裝依賴

```bash
# 使用 uv 安裝 Python 依賴
uv sync
```

### 2. 設定環境變數

複製範例設定檔：

```bash
cp .env.example .env
```

編輯 `.env`：

```bash
# 資料庫設定
DB_NAME=jaba_ai
DB_USER=jaba_ai
DB_PASSWORD=your_secure_password
DB_HOST=localhost
DB_PORT=5433

# 應用程式設定
APP_PORT=8089

# 初始超級管理員（首次啟動時自動建立）
INIT_ADMIN_USERNAME=admin
INIT_ADMIN_PASSWORD=your_admin_password

# Claude Code (CLI) 工作目錄
PROJECT_ROOT=/path/to/jaba-ai

# LINE Bot 設定
LINE_CHANNEL_SECRET=your_line_channel_secret
LINE_CHANNEL_ACCESS_TOKEN=your_line_channel_access_token

# 公開 URL（用於申請連結）
APP_URL=https://your-domain.com/jaba-ai
```

### 3. 啟動資料庫

使用 Docker Compose：

```bash
docker-compose up -d postgres
```

或手動建立 PostgreSQL 資料庫：

```sql
CREATE DATABASE jaba_ai;
CREATE USER jaba_ai WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE jaba_ai TO jaba_ai;
```

### 4. 執行資料庫遷移

```bash
# 使用 uv（推薦）
uv run alembic upgrade head

# 或直接使用 alembic
alembic upgrade head
```

這會建立所有資料表並初始化 AI 提示詞。

### 5. 啟動應用程式

**一鍵啟動（推薦）：**

```bash
# 啟動資料庫 + 遷移 + 應用程式
./scripts/start.sh

# 僅啟動資料庫
./scripts/start.sh --db-only

# 僅執行遷移
./scripts/start.sh --migrate

# 僅啟動應用程式
./scripts/start.sh --app-only

# 停止所有服務
./scripts/start.sh --stop
```

**開發模式：**

```bash
python main.py
# 或
uv run python main.py
```

**使用 uvicorn：**

```bash
uvicorn main:socket_app --host 0.0.0.0 --port 8089 --reload
```

---

## LINE Bot 設定

### 1. 建立 LINE Bot

1. 前往 [LINE Developers Console](https://developers.line.biz/console/)
2. 建立新的 Provider（如已有可跳過）
3. 建立新的 Messaging API Channel
4. 記錄以下資訊：
   - Channel Secret
   - Channel Access Token（需發行）

### 2. 設定 Webhook

1. 在 Channel 設定頁面找到「Messaging API」分頁
2. 設定 Webhook URL：`https://your-domain.com/api/webhook/line`
3. 開啟「Use webhook」
4. 關閉「Auto-reply messages」和「Greeting messages」（由 Bot 處理）

### 3. 更新環境變數

```bash
LINE_CHANNEL_SECRET=你的 Channel Secret
LINE_CHANNEL_ACCESS_TOKEN=你的 Channel Access Token
```

---

## Claude Code CLI 設定

本系統使用 Claude Code CLI 進行 AI 對話與菜單辨識。

### 1. 安裝 Claude Code

**方法一：Native Install（推薦）**

macOS / Linux / WSL：
```bash
curl -fsSL https://claude.ai/install.sh | bash
```

Windows PowerShell：
```powershell
irm https://claude.ai/install.ps1 | iex
```

**方法二：Homebrew（macOS）**

```bash
brew install --cask claude-code
```

**方法三：NPM**

需要 Node.js 18+：
```bash
npm install -g @anthropic-ai/claude-code
```

### 2. 首次登入

安裝完成後，首次執行 `claude` 命令時會自動引導登入流程：

```bash
claude
```

按照提示完成認證（需要 [Claude.ai](https://claude.ai) 帳號或 [Anthropic Console](https://console.anthropic.com/) 帳號）。

若需要重新登入，可在 Claude Code 互動模式中輸入：

```
/logout
/login
```

### 3. 驗證安裝

```bash
claude -p "hello"
```

### 4. 設定環境變數

確保 `PROJECT_ROOT` 指向正確的專案目錄：

```bash
PROJECT_ROOT=/home/user/jaba-ai
```

> **注意**：Claude Code 會自動保持更新。更多進階設定請參考 [官方文件](https://code.claude.com/docs)。

---

## 生產環境部署（可選）

以下為生產環境的建議設定，開發環境可略過。

### 使用 systemd 服務

專案已提供 service 檔案和安裝腳本：

```bash
# 安裝服務
sudo ./scripts/install-service.sh

# 啟動服務
sudo systemctl start jaba-ai

# 查看狀態
sudo systemctl status jaba-ai

# 查看即時日誌
journalctl -u jaba-ai -f

# 移除服務
sudo ./scripts/uninstall-service.sh
```

> **注意**：安裝前請編輯 `scripts/jaba-ai.service`，確認 `User`、`WorkingDirectory`、`EnvironmentFile` 和 `PATH` 符合實際環境。

### 使用 Nginx 反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    # 重導向到 HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    # API 和靜態檔案
    location / {
        proxy_pass http://127.0.0.1:8089;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # Socket.IO
    location /socket.io/ {
        proxy_pass http://127.0.0.1:8089/socket.io/;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 資料庫維護

### 查詢資料庫

使用 Docker 執行 SQL 指令：

```bash
docker exec jaba-ai-postgres psql -U jaba_ai -d jaba_ai -c "YOUR SQL HERE"
```

### 備份

```bash
docker exec jaba-ai-postgres pg_dump -U jaba_ai jaba_ai > backup_$(date +%Y%m%d).sql
```

### 還原

```bash
docker exec -i jaba-ai-postgres psql -U jaba_ai -d jaba_ai < backup.sql
```

### 重建資料庫

```bash
# 降級到初始狀態
uv run alembic downgrade base

# 重新升級（會清除所有資料並重建）
uv run alembic upgrade head
```

### 手動清理舊對話

```bash
# 透過 API（需要管理員 token）
curl -X POST "http://localhost:8089/api/admin/maintenance/cleanup-chat?retention_days=365" \
  -H "Authorization: Bearer <token>"
```

---

## 環境變數說明

| 變數 | 必填 | 預設值 | 說明 |
|-----|------|-------|------|
| `DB_HOST` | 否 | localhost | 資料庫主機 |
| `DB_PORT` | 否 | 5433 | 資料庫連接埠（Docker 映射） |
| `DB_NAME` | 否 | jaba_ai | 資料庫名稱 |
| `DB_USER` | 否 | jaba_ai | 資料庫使用者 |
| `DB_PASSWORD` | 否 | jaba_ai_secret | 資料庫密碼 |
| `APP_PORT` | 否 | 8089 | 應用程式連接埠 |
| `INIT_ADMIN_USERNAME` | 否 | admin | 初始管理員帳號 |
| `INIT_ADMIN_PASSWORD` | 否 | admin123 | 初始管理員密碼（首次啟動後無法透過 UI 修改） |
| `LINE_CHANNEL_SECRET` | 是 | - | LINE Channel Secret |
| `LINE_CHANNEL_ACCESS_TOKEN` | 是 | - | LINE Channel Access Token |
| `PROJECT_ROOT` | 否 | /home/ct/SDD/jaba-ai | Claude Code (CLI) 工作目錄 |
| `APP_URL` | 否 | - | 公開 URL（用於申請連結） |
| `SECURITY_BAN_THRESHOLD` | 否 | 5 | 安全過濾觸發次數上限（超過則封鎖） |
| `CHAT_HISTORY_LIMIT` | 否 | 40 | 傳給 AI 的對話歷史筆數 |

---

## 監控與日誌

### 查看日誌

```bash
# 開發環境：直接執行時的輸出
uv run python main.py 2>&1 | tee app.log

# 生產環境（已設定 systemd）：查看服務日誌
journalctl -u jaba-ai -f
```

### 健康檢查

```bash
curl http://localhost:8089/health
# {"status": "healthy"}
```

### 對話統計

```bash
curl -X GET "http://localhost:8089/api/admin/maintenance/chat-stats" \
  -H "Authorization: Bearer <token>"
```

---

## 常見問題

### Claude Code 找不到

確認 Claude Code 已安裝並在 PATH 中：

```bash
which claude
```

如使用 Native Install，預設安裝位置為 `~/.local/bin/claude`。確認 PATH 包含此目錄：
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

如使用 NPM 安裝，確認 Node.js 的 bin 目錄在 PATH 中：
```bash
echo 'export PATH="$(npm config get prefix)/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
```

### 資料庫連線失敗

1. 確認 PostgreSQL 服務運行中
2. 確認連接埠正確（Docker 預設映射到 5433）
3. 確認使用者權限

### LINE Webhook 驗證失敗

1. 確認 Channel Secret 正確
2. 確認 Webhook URL 可從外網存取
3. 確認使用 HTTPS

### AI 回應超時

1. 檢查網路連線
2. 確認 Claude Code 認證有效（執行 `claude` 確認是否需要重新登入）
3. 考慮增加超時時間（預設 120 秒）

### 修改超級管理員密碼

目前沒有 UI 可修改密碼，有兩種方式：

**方法一：刪除後重建**

```bash
# 1. 刪除資料庫中的管理員
docker exec jaba-ai-postgres psql -U jaba_ai -d jaba_ai -c "DELETE FROM super_admins;"

# 2. 修改 .env 中的 INIT_ADMIN_PASSWORD

# 3. 重啟應用程式（會自動建立新管理員）
sudo systemctl restart jaba-ai
```

**方法二：直接修改資料庫**

```bash
# 1. 產生新密碼的 SHA-256 hash
python3 -c "import hashlib; print(hashlib.sha256('新密碼'.encode()).hexdigest())"

# 2. 更新資料庫（將 hash 值替換到下方指令）
docker exec jaba-ai-postgres psql -U jaba_ai -d jaba_ai -c \
  "UPDATE super_admins SET password_hash='產生的hash值' WHERE username='admin';"
```

> **注意**：方法二不會被 `.env` 的 `INIT_ADMIN_PASSWORD` 覆蓋，因為系統只在沒有任何管理員時才會自動建立。

---

## 更新部署

```bash
# 拉取最新程式碼
git pull origin master

# 安裝新依賴
uv sync

# 執行資料庫遷移
uv run alembic upgrade head

# 重啟應用程式
# 開發環境：重新執行 ./scripts/start.sh 或 uv run python main.py
# 生產環境（已設定 systemd）：sudo systemctl restart jaba-ai
```

## OpenSpec (SDD 規格驅動開發)

本專案使用 [OpenSpec](https://github.com/Fission-AI/OpenSpec) 進行規格驅動開發（Spec-Driven Development）。核心理念是在寫程式碼前，人類與 AI 先對「要做什麼」達成共識。透過 Claude Code 的斜線命令操作：

### 三階段工作流程

| 階段 | 命令 | 說明 |
|-----|------|------|
| 1. 提案 | `/openspec:proposal` | 建立變更提案、tasks.md、spec deltas |
| 2. 實施 | `/openspec:apply` | 依序完成 tasks.md 中的任務 |
| 3. 歸檔 | `/openspec:archive` | 部署後歸檔，更新 specs/ 目錄 |

### CLI 常用命令

```bash
openspec list                  # 查看進行中的變更
openspec list --specs          # 查看已部署的規格
openspec spec view <spec-name> # 查看規格詳情
openspec validate --all        # 驗證所有規格和變更
openspec archive <id> -y       # 歸檔變更（非互動模式）
```

### 目錄結構

```
openspec/
├── project.md           # 專案約定與慣例
├── specs/               # 系統規格（唯一真實來源 source of truth）
│   └── [capability]/
│       └── spec.md
├── changes/             # 變更提案（spec deltas）
│   └── [change-id]/
│       ├── proposal.md  # 變更說明（Why、What、Impact）
│       ├── tasks.md     # 實施任務清單
│       ├── design.md    # 技術設計（選用）
│       └── specs/       # 規格差異
└── changes/archive/     # 已完成的變更歷史
```

> **優勢**：AI 只需處理隔離的 spec deltas，而非整個程式碼庫，提升 token 效率。

詳細說明請參考 `openspec/AGENTS.md` 和 [OpenSpec 官方文件](https://github.com/Fission-AI/OpenSpec)。
