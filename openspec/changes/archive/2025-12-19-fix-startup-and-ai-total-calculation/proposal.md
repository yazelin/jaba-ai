# Change: 修復啟動腳本與 AI 訂單計算問題

## Why

1. **systemd 服務啟動失敗**：jaba-ai.service 使用 `uv run python main.py` 啟動，但因為工作目錄問題導致失敗
2. **AI 代點金額計算錯誤**：用戶反映「代點 3 份 100 元餐點和 1 份 100 元餐點，總共只要 100 元」，預期應該是 400 元

## What Changes

### 問題 1：啟動腳本問題

從 systemd 日誌可見：
- `ExecStartPre=/usr/bin/docker compose up -d postgres` 成功
- `ExecStart=/home/ct/.local/bin/uv run python main.py` 失敗 (exit code 1)

可能原因：
- 工作目錄未正確設定（systemd 需要 WorkingDirectory）
- start.sh 使用相對路徑但 systemd 不在專案目錄執行

### 問題 2：AI 訂單總金額計算 (已確認根本原因)

**資料庫實際狀態**：
```
Order 9d2b72fc... total_amount=100
  ├── 魚排飯: quantity=1, subtotal=100 (建立於 03:00:35)
  └── 炒羊肉飯: quantity=3, subtotal=300 (建立於 03:02:19)
```

**根本原因**：`calculate_total` 函數在 `app/repositories/order_repo.py:224` 使用 `selectinload(Order.items)` 重新載入訂單品項，但 SQLAlchemy 的 identity map 可能返回快取的 Order 物件，導致 `order.items` 不包含剛新增的品項。

**修復方案**：在查詢前使用 `session.expire(order)` 或添加 `execution_options(populate_existing=True)` 強制重新載入。

## Impact

- Affected specs: core
- Affected code:
  - `scripts/start.sh`（如需調整）
  - `app/repositories/order_repo.py:calculate_total` **需修改**
