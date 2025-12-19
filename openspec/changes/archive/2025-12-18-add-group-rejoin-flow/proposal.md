# Change: 新增群組重新加入 Bot 的處理流程

## Why
當 Bot 被踢出群組後又重新加入時，目前系統會將群組視為「尚未開通」，要求重新申請。
這個行為不夠彈性，應該讓群組管理者選擇要「恢復舊設定」還是「重新申請」。

## What Changes
- 當 Bot 重新加入一個曾被踢出（status="inactive"）的群組時，發送選擇訊息
- 提供兩個選項：
  - **恢復舊設定**：直接將 status 改為 "active"，保留原本的店家和設定
  - **重新申請**：將 status 改為 "pending"，需重新審核
- 訊息說明要清楚，讓使用者理解兩個選項的差異
- 如果選擇「重新申請」且之後填寫不同的群組代碼，原本的群組專屬店家會失聯

## Impact
- Affected specs: `line-bot`
- Affected code: `app/services/line_service.py` (handle_join, handle_postback)
