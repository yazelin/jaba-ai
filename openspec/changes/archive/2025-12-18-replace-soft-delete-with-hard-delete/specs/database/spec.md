# database Specification Delta

## MODIFIED Requirements

### Requirement: User Data Model
系統 SHALL 儲存使用者資料，包含 LINE User ID、顯示名稱、個人偏好。刪除使用者時直接從資料庫移除。

#### Scenario: 使用者首次互動
- **WHEN** 使用者首次與 Bot 互動
- **THEN** 系統自動建立使用者記錄，儲存 LINE User ID 和顯示名稱

#### Scenario: 個人偏好儲存
- **WHEN** 使用者設定個人偏好（稱呼、飲食限制、過敏、飲料偏好）
- **THEN** 系統將偏好儲存為 JSONB 格式

#### Scenario: 使用者刪除
- **WHEN** 系統需要刪除使用者
- **THEN** 系統直接從資料庫移除使用者記錄（硬刪除）

### Requirement: Group Data Model
系統 SHALL 儲存群組資料，包含 LINE Group ID、群組名稱、狀態。刪除群組時直接從資料庫移除。

#### Scenario: 群組狀態管理
- **WHEN** 群組申請審核通過
- **THEN** 群組狀態從 pending 變更為 active

#### Scenario: 群組成員追蹤
- **WHEN** 使用者在群組中互動
- **THEN** 系統記錄使用者為該群組成員

#### Scenario: 群組刪除
- **WHEN** 管理員刪除群組
- **THEN** 系統直接從資料庫移除群組記錄（硬刪除）

### Requirement: Store Data Model
系統 SHALL 儲存店家資料，包含名稱、電話、地址、描述、狀態。刪除店家時直接從資料庫移除。

#### Scenario: 店家全域共用
- **WHEN** 管理員建立新店家
- **THEN** 所有群組都可以將該店家設為今日店家

#### Scenario: 店家刪除
- **WHEN** 管理員刪除店家
- **THEN** 系統直接從資料庫移除店家記錄（硬刪除）
