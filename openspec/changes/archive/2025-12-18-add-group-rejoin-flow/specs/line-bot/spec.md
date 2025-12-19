## ADDED Requirements

### Requirement: Group Join Handling
Bot 加入群組時 SHALL 根據群組狀態提供適當回應。

#### Scenario: Bot 加入新群組（無記錄）
- **WHEN** Bot 加入一個從未使用過的群組
- **THEN** 建立新群組記錄（status="pending"）
- **AND** 發送申請開通的說明訊息

#### Scenario: Bot 加入已啟用群組
- **WHEN** Bot 加入一個 status="active" 的群組
- **THEN** 發送歡迎訊息，告知可以開始點餐

#### Scenario: Bot 重新加入曾被踢出的群組
- **WHEN** Bot 加入一個 status="inactive" 的群組
- **THEN** 發送選擇訊息，包含：
  - 群組名稱和曾使用過的說明
  - 「恢復舊設定」按鈕：保留原本的店家和設定
  - 「重新申請」按鈕：需重新審核，若填不同代碼則舊店家會失聯
- **AND** 訊息 SHALL 清楚說明兩個選項的差異

#### Scenario: Bot 加入被停用的群組
- **WHEN** Bot 加入一個 status="suspended" 的群組
- **THEN** 發送「此群組已被管理員停用」的訊息
- **AND** 不提供恢復選項

## ADDED Requirements

### Requirement: Rejoin Choice Handling
系統 SHALL 處理使用者在重新加入群組時的選擇。

#### Scenario: 使用者選擇恢復舊設定
- **WHEN** 使用者點擊「恢復舊設定」按鈕
- **THEN** 將群組 status 改為 "active"
- **AND** 發送「已恢復！可以開始點餐了」的確認訊息

#### Scenario: 使用者選擇重新申請
- **WHEN** 使用者點擊「重新申請」按鈕
- **THEN** 將群組 status 改為 "pending"
- **AND** 發送申請開通的說明訊息（與新群組相同）
