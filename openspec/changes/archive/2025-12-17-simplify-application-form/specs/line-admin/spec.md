# line-admin Spec Delta

## ADDED Requirements

### Requirement: Application Page Description
申請頁面 SHALL 使用「群組代碼」取代「管理密碼」，並清楚說明其用途與非保密性質。

#### Scenario: 群組代碼說明
- **WHEN** 使用者查看申請頁面的群組代碼欄位
- **THEN** 欄位名稱為「群組代碼」
- **AND** 說明文字包含：
  - 「用於登入 LINE 管理後台」
  - 「在群組中輸入『管理員 [代碼]』啟用管理員身份」
  - 「此代碼會在群組對話中顯示，不具保密性」
- **AND** 輸入框 placeholder 為「設定一組方便記憶的代碼（4-20字元）」

#### Scenario: 簡化申請欄位
- **WHEN** 使用者填寫申請表單
- **THEN** 必填欄位為：
  - LINE 群組 ID
  - 群組名稱
  - 聯絡資訊（合併原申請人姓名和聯絡方式）
  - 群組代碼
- **AND** 不顯示「申請原因」欄位

### Requirement: Change Group Code
系統 SHALL 支援變更群組代碼功能，使用「群組代碼」術語。

#### Scenario: 變更群組代碼介面
- **WHEN** 管理員點擊「變更群組代碼」按鈕
- **THEN** 顯示變更面板
- **AND** 欄位包含：目前代碼、新代碼、確認新代碼
- **AND** 所有文字使用「代碼」而非「密碼」

#### Scenario: 變更成功
- **GIVEN** 管理員已登入
- **WHEN** 輸入正確的目前代碼和有效的新代碼
- **THEN** 系統更新群組代碼
- **AND** 顯示「群組代碼變更成功」

### Requirement: Admin Login
系統 SHALL 使用「群組代碼」術語於登入介面。

#### Scenario: 登入介面
- **WHEN** 使用者查看管理員登入面板
- **THEN** 提示文字使用「群組代碼」
- **AND** placeholder 為「請輸入群組代碼」
