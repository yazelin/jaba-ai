## ADDED Requirements

### Requirement: Application Startup

系統 SHALL 支援以下啟動方式：
1. 本地開發：`./scripts/start.sh` 或 `uv run python main.py`
2. systemd 服務：透過 jaba-ai.service 自動啟動

#### Scenario: systemd 服務啟動
- **WHEN** 執行 `systemctl start jaba-ai`
- **THEN** PostgreSQL 容器應自動啟動
- **AND** Python 應用程式應在容器就緒後啟動
- **AND** 應用程式應監聽於設定的 APP_PORT（預設 8089）

### Requirement: Order Total Calculation

系統 SHALL 正確計算訂單總金額：
- 每個品項的小計 = 單價 × 數量
- 訂單總金額 = 所有品項小計的加總

#### Scenario: 多品項訂單計算
- **GIVEN** 用戶訂購：
  - 3 份 $100 餐點
  - 1 份 $100 餐點
- **WHEN** 系統計算訂單總金額
- **THEN** 總金額應為 $400（= 100×3 + 100×1）

#### Scenario: AI 代點多品項
- **GIVEN** AI 解析用戶訊息為多個品項
- **WHEN** AI 回傳 `group_create_order` action
- **THEN** items 陣列中每個品項應包含正確的 quantity
- **AND** 系統應正確計算每個品項的 subtotal
- **AND** 訂單總金額應為所有 subtotal 的加總
