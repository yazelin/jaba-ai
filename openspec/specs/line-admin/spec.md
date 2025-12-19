# line-admin Specification

## Purpose
TBD - created by archiving change simplify-application-form. Update Purpose after archive.
## Requirements
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

### Requirement: Tab Navigation
超管後台 SHALL 使用標籤頁導航組織功能模組。

#### Scenario: 標籤頁結構
- **WHEN** 超管進入後台
- **THEN** 顯示以下標籤頁：[店家管理] [群組管理] [使用者管理] [違規記錄] [系統設定]
- **AND** 點擊標籤可切換對應內容區域

### Requirement: Floating AI Chat Widget
AI 助手對話框 SHALL 以懸浮式設計呈現，不佔用主要畫面空間。

#### Scenario: 懸浮按鈕顯示
- **WHEN** 對話框收合時
- **THEN** 右下角顯示圓形懸浮按鈕
- **AND** 按鈕顯示 Jaba 圖示

#### Scenario: 對話框展開
- **WHEN** 使用者點擊懸浮按鈕
- **THEN** 展開對話框（360px 寬 × 500px 高）
- **AND** 顯示標題列、對話區域、輸入區域

### Requirement: User Management Panel
超管後台 SHALL 提供使用者管理功能。

#### Scenario: 使用者列表
- **WHEN** 超管進入使用者管理標籤
- **THEN** 顯示使用者列表含：頭像、名稱、LINE ID、群組數、訂單數、狀態
- **AND** 支援搜尋、狀態篩選、分頁

#### Scenario: 封鎖使用者
- **WHEN** 超管點擊封鎖按鈕並確認
- **THEN** 呼叫 `POST /api/admin/users/{user_id}/ban`
- **AND** 設定 `is_banned=True`, `banned_at=now()`

#### Scenario: 解除封鎖
- **WHEN** 超管點擊解封按鈕並確認
- **THEN** 呼叫 `POST /api/admin/users/{user_id}/unban`
- **AND** 設定 `is_banned=False`, `banned_at=None`

### Requirement: Enhanced Group Management Panel
超管後台 SHALL 提供增強的群組管理功能。

#### Scenario: 群組列表增強
- **WHEN** 超管進入群組管理標籤
- **THEN** 顯示群組列表含：名稱、LINE ID、代碼、狀態、成員數、管理員數、建立時間
- **AND** 支援搜尋、狀態篩選、分頁

#### Scenario: 停用群組
- **WHEN** 超管點擊停用按鈕並確認
- **THEN** 呼叫 `POST /api/admin/groups/{group_id}/suspend`
- **AND** 設定群組 status="suspended"

#### Scenario: 啟用群組
- **WHEN** 超管點擊啟用按鈕並確認
- **THEN** 呼叫 `POST /api/admin/groups/{group_id}/activate`
- **AND** 設定群組 status="active"

### Requirement: Security Logs Panel
超管後台 SHALL 顯示違規記錄檢視面板。

#### Scenario: 違規記錄統計
- **WHEN** 超管進入違規記錄標籤
- **THEN** 顯示統計卡片：今日違規數、本週違規數、總違規數

#### Scenario: 違規記錄列表
- **WHEN** 超管瀏覽違規記錄
- **THEN** 顯示列表含：時間、使用者、群組、訊息、原因、操作
- **AND** 支援日期範圍篩選、群組篩選、分頁

