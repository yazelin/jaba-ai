# Implementation Tasks

## 1. 專案初始化
- [x] 1.1 建立 pyproject.toml 依賴配置
- [x] 1.2 建立 docker-compose.yml (PostgreSQL + nginx)
- [x] 1.3 建立 .env.example 環境變數範本
- [x] 1.4 建立 alembic.ini 和 migrations 目錄結構
- [x] 1.5 建立 app/ 目錄結構

## 2. 資料庫基礎
- [x] 2.1 建立 app/database.py 資料庫連線模組
- [x] 2.2 建立 app/config.py 設定管理
- [x] 2.3 建立初始 migration (所有資料表)

## 3. Models 定義
- [x] 3.1 建立 User model
- [x] 3.2 建立 Group, GroupApplication, GroupMember, GroupAdmin models
- [x] 3.3 建立 Store, Menu, MenuCategory, MenuItem models
- [x] 3.4 建立 GroupTodayStore model
- [x] 3.5 建立 OrderSession, Order, OrderItem models
- [x] 3.6 建立 ChatMessage model
- [x] 3.7 建立 SystemConfig, AiPrompt models

## 4. Repository 層
- [x] 4.1 建立 UserRepository
- [x] 4.2 建立 GroupRepository
- [x] 4.3 建立 StoreRepository
- [x] 4.4 建立 MenuRepository
- [x] 4.5 建立 OrderRepository
- [x] 4.6 建立 ChatRepository

## 5. 服務層
- [x] 5.1 建立 AiService (Claude 整合)
- [x] 5.2 建立 OrderService (點餐業務邏輯)
- [x] 5.3 建立 LineService (LINE Bot 訊息處理)
- [x] 5.4 建立 MenuService (菜單辨識整合在 MenuService 中)

## 6. API 路由
- [x] 6.1 建立 LINE Webhook 路由 (/callback)
- [x] 6.2 建立公開 API 路由 (/api/stores, /api/menu, /api/today)
- [x] 6.3 建立看板 API 路由 (/api/board/orders, /api/board/chat, /api/board/today-stores)
- [x] 6.4 建立管理員 API 路由 (/api/admin/*)
- [x] 6.5 建立 LINE 管理員 API 路由 (/api/line-admin/*)

## 7. 前端頁面
- [x] 7.1 建立 board.html (看板頁面) - 保持原有設計風格
- [x] 7.2 建立 admin.html (超級管理員頁面) - 保持原有設計風格，含 AI 對話框
- [x] 7.3 遷移 static/css/style.css
- [x] 7.4 **重要**: 遷移 jaba icon 和所有圖片資源
- [x] 7.5 新增群組選擇器功能
- [x] 7.6 新增群組申請審核介面 (超級管理員後台內)

## 8. Socket.IO 整合
- [x] 8.1 整合 Socket.IO 到 FastAPI (main.py)
- [x] 8.2 實作訂單更新廣播
- [x] 8.3 實作聊天訊息廣播

## 9. LINE Bot 功能
- [x] 9.1 實作 Webhook 簽章驗證
- [x] 9.2 實作群組點餐 Session 管理 (LineService)
- [x] 9.3 實作個人偏好設定 (1v1 聊天)
- [x] 9.4 實作群組管理員功能 (line_admin.py)

## 10. AI 整合
- [x] 10.1 實作群組點餐 AI 對話 (ai_service.py)
- [x] 10.2 實作管理員 AI 對話
- [x] 10.3 實作菜單辨識功能 (menu_service.py)
- [x] 10.4 AI 提示詞管理 API (admin.py)

## 11. 權限與認證
- [x] 11.1 實作超級管理員驗證 (密碼) - admin.py /verify
- [x] 11.2 實作 LINE 管理員簡易後台密碼產生與驗證 - line_admin.py /login
- [x] 11.3 實作群組申請審核流程 - admin.py /applications/*

## 12. 歷史訂單與提示詞管理
- [x] 12.1 實作歷史訂單查詢 API - admin.py /groups/{id}/orders
- [x] 12.2 實作 AI 提示詞管理 API - admin.py /prompts

## 13. 效能與監控
- [x] 13.1 實作記憶體快取（dict + 更新時清除）- cache_service.py
- [x] 13.2 實作菜單辨識圖片壓縮（不儲存）- menu_service.py

## 14. 測試與部署
- [x] 14.1 測試 LINE Webhook
- [x] 14.2 測試群組點餐流程
- [x] 14.3 測試管理員功能
- [x] 14.4 測試看板功能
- [x] 14.5 建立 nginx 設定
- [x] 14.6 部署到內網伺服器
