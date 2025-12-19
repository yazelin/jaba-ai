# Change: 整合 jaba 與 jaba-line-bot 專案

## Why
目前 jaba 和 jaba-line-bot 分別部署在兩台伺服器上，增加維運複雜度。整合為單一專案可以：
- 減少維運成本和複雜度
- 統一程式碼基礎，便於維護
- 提供更完整的功能整合
- 支援新的群組申請審核機制和 LINE 管理員功能

## What Changes

### 架構變更
- **BREAKING**: 從 JSON 檔案存儲遷移至 PostgreSQL 資料庫
- 整合 LINE Bot Webhook 到主應用程式
- 移除 Gemini CLI 支援，僅使用 Claude

### 新功能
- 群組申請審核機制（後台申請表單 → 超級管理員審核）
- LINE 管理員認證（LINE User ID 綁定，超級管理員指定）
- 群組管理員透過 LINE 管理功能（等同後台管理權限）
- 今日菜單以群組為單位

### 資料模型變更
- 所有資料表以 UUID 為主鍵
- 群組為核心組織單位
- 店家為全域共用資源
- 新增群組申請、群組管理員等資料表

### 保留功能
- 看板 UI（支援群組選擇）
- 管理員後台 UI
- 群組點餐 Session 機制
- 個人偏好設定
- AI 菜單辨識
- Socket.IO 即時更新

## Impact
- Affected specs: core, line-bot, admin, database (全新建立)
- Affected code: 全部重寫
- Migration: 需要資料遷移腳本將既有 JSON 資料匯入 PostgreSQL
