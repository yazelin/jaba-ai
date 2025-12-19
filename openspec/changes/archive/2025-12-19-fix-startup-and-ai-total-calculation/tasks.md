## 1. 調查與診斷（已完成）

- [x] 1.1 啟動 PostgreSQL 容器以查看 AI 日誌
- [x] 1.2 查詢 ai_logs 表，找出代點訂單的 raw_response
- [x] 1.3 分析 AI 回傳的 actions 結構是否正確
- [x] 1.4 確認根本原因：`calculate_total` 的 `selectinload` 沒有強制重新載入

## 2. 修復 AI 訂單計算問題

- [x] 2.1 修改 `app/repositories/order_repo.py:calculate_total`，改用直接 SQL SUM 查詢
- [x] 2.2 驗證程式碼語法正確

## 3. 修復啟動問題

- [x] 3.1 確認 systemd service 檔案設定正確（WorkingDirectory 已設定）
- [x] 3.2 驗證服務正常運行（curl /health 返回 healthy）

## 4. 資料修復

- [x] 4.1 修復現有錯誤的訂單資料
  - Order 9d2b72fc... total_amount: 100.00 → 400.00
