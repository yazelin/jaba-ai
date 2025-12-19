#!/bin/bash
# Jaba AI 開發測試啟動腳本

set -e

# 顏色定義
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 專案根目錄
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 輸出函數
info() { echo -e "${BLUE}[INFO]${NC} $1"; }
success() { echo -e "${GREEN}[OK]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# 顯示使用說明
show_help() {
    echo "使用方式: $0 [選項]"
    echo ""
    echo "選項:"
    echo "  --db-only      僅啟動資料庫"
    echo "  --app-only     僅啟動應用程式 (假設資料庫已運行)"
    echo "  --migrate      僅執行資料庫遷移"
    echo "  --stop         停止所有服務"
    echo "  --restart      重啟所有服務"
    echo "  --logs         查看資料庫日誌"
    echo "  --help         顯示此說明"
    echo ""
    echo "預設: 啟動資料庫 + 遷移 + 應用程式"
}

# 檢查相依工具
check_dependencies() {
    info "檢查相依工具..."

    if ! command -v docker &> /dev/null; then
        error "未安裝 docker"
    fi

    if ! command -v uv &> /dev/null; then
        error "未安裝 uv (Python 套件管理器)"
    fi

    success "相依工具檢查通過"
}

# 載入環境變數
load_env() {
    if [ -f "$PROJECT_DIR/.env" ]; then
        info "載入 .env 環境變數..."
        set -a
        source "$PROJECT_DIR/.env"
        set +a
        success "環境變數已載入"
    else
        warn ".env 檔案不存在，使用預設值"
    fi
}

# 啟動資料庫
start_db() {
    info "啟動 PostgreSQL..."
    docker compose up -d postgres
    success "PostgreSQL 容器已啟動"
}

# 等待資料庫就緒
wait_for_db() {
    info "等待資料庫就緒..."

    local max_attempts=30
    local attempt=1

    while [ $attempt -le $max_attempts ]; do
        if docker compose exec -T postgres pg_isready -U "${DB_USER:-jaba}" -d "${DB_NAME:-jaba}" &> /dev/null; then
            success "資料庫已就緒"
            return 0
        fi

        echo -n "."
        sleep 1
        ((attempt++))
    done

    echo ""
    error "資料庫啟動逾時"
}

# 執行資料庫遷移
run_migrations() {
    info "執行資料庫遷移..."
    uv run alembic upgrade head
    success "資料庫遷移完成"
}

# 檢查並清理佔用的 port
check_and_kill_port() {
    local port="${APP_PORT:-8089}"
    local pid=$(lsof -t -i ":$port" 2>/dev/null | head -1)

    if [ -n "$pid" ]; then
        warn "Port $port 已被佔用 (PID: $pid)"
        info "正在停止舊程序..."
        kill $pid 2>/dev/null || true
        sleep 1

        # 確認是否已停止
        if lsof -i ":$port" &>/dev/null; then
            warn "程序未停止，強制終止..."
            kill -9 $pid 2>/dev/null || true
            sleep 1
        fi

        success "舊程序已停止"
    fi
}

# 啟動應用程式
start_app() {
    check_and_kill_port

    info "啟動應用程式..."
    echo -e "${GREEN}========================================${NC}"
    echo -e "${GREEN}  Jaba AI 啟動於 http://localhost:${APP_PORT:-8089}${NC}"
    echo -e "${GREEN}========================================${NC}"
    echo ""
    uv run python main.py
}

# 停止服務
stop_services() {
    info "停止所有服務..."
    docker compose down
    success "服務已停止"
}

# 查看日誌
show_logs() {
    docker compose logs -f postgres
}

# 主程式
main() {
    case "${1:-}" in
        --help|-h)
            show_help
            exit 0
            ;;
        --db-only)
            check_dependencies
            load_env
            start_db
            wait_for_db
            info "資料庫已啟動，連線資訊:"
            echo "  Host: localhost:${DB_PORT:-5432}"
            echo "  Database: ${DB_NAME:-jaba}"
            echo "  User: ${DB_USER:-jaba}"
            ;;
        --app-only)
            check_dependencies
            load_env
            start_app
            ;;
        --migrate)
            check_dependencies
            load_env
            run_migrations
            ;;
        --stop)
            stop_services
            ;;
        --restart)
            stop_services
            sleep 2
            check_dependencies
            load_env
            start_db
            wait_for_db
            run_migrations
            start_app
            ;;
        --logs)
            show_logs
            ;;
        "")
            check_dependencies
            load_env
            start_db
            wait_for_db
            run_migrations
            start_app
            ;;
        *)
            error "未知選項: $1 (使用 --help 查看說明)"
            ;;
    esac
}

main "$@"
