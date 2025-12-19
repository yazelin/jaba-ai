# admin Specification

## Purpose
TBD - created by archiving change integrate-jaba-projects. Update Purpose after archive.
## Requirements
### Requirement: Super Admin Authentication
系統 SHALL 提供超級管理員驗證機制。

#### Scenario: 密碼驗證
- **WHEN** 使用者在管理後台輸入密碼
- **THEN** 系統驗證密碼並授予管理權限

#### Scenario: Session 管理
- **WHEN** 驗證成功
- **THEN** 系統建立管理 Session

### Requirement: Group Application Management
系統 SHALL 提供群組申請審核功能。

#### Scenario: 提交申請
- **WHEN** 使用者在後台填寫群組申請表單
- **THEN** 系統建立申請記錄，狀態為 pending

#### Scenario: 申請審核
- **WHEN** 超級管理員審核申請
- **THEN** 系統更新申請狀態（approved/rejected）並建立/更新群組記錄

#### Scenario: 申請列表
- **WHEN** 超級管理員查看申請列表
- **THEN** 系統顯示所有待審核和已處理的申請

### Requirement: Group Admin Management
系統 SHALL 提供群組管理員指定功能。

#### Scenario: 指定管理員
- **WHEN** 超級管理員在後台指定某使用者為群組管理員
- **THEN** 系統建立 group_admin 關聯記錄

#### Scenario: 移除管理員
- **WHEN** 超級管理員移除群組管理員
- **THEN** 系統刪除 group_admin 關聯記錄

#### Scenario: 管理員列表
- **WHEN** 超級管理員查看群組詳情
- **THEN** 系統顯示該群組的所有管理員

### Requirement: LINE Admin Functions
系統 SHALL 允許群組管理員透過 LINE 執行管理功能。

#### Scenario: 管理員識別
- **WHEN** 使用者在群組中發送管理指令
- **THEN** 系統檢查該使用者是否為該群組的管理員

#### Scenario: 設定今日店家
- **WHEN** 群組管理員在 LINE 中說「今天吃xxx」
- **THEN** AI 解析並設定該群組的今日店家

#### Scenario: 更新菜單價格
- **WHEN** 群組管理員在 LINE 中說「xxx 漲價到 100 元」
- **THEN** AI 解析並更新菜單品項價格

#### Scenario: 代理點餐
- **WHEN** 群組管理員在 LINE 中說「幫小明點xxx」
- **THEN** AI 解析並為指定使用者建立訂單

#### Scenario: 訂單管理
- **WHEN** 群組管理員在 LINE 中說「刪除小明的訂單」
- **THEN** AI 解析並刪除指定使用者的訂單

### Requirement: LINE Admin Portal
系統 SHALL 提供 LINE 管理員簡易後台頁面，使用超級管理員產生的密碼登入。

#### Scenario: 管理員密碼產生
- **WHEN** 超級管理員指定某使用者為群組管理員
- **THEN** 系統產生專屬密碼供該管理員登入簡易後台

#### Scenario: 管理員登入
- **WHEN** LINE 管理員輸入密碼
- **THEN** 系統驗證密碼並顯示其管理的群組

#### Scenario: 查看群組點餐狀態
- **WHEN** LINE 管理員登入簡易後台
- **THEN** 可以查看自己管理的群組目前點餐狀態（是否在點餐中、訂單數量、歷史訂單）

### Requirement: Super Admin Backend
系統 SHALL 提供超級管理員後台介面，UI 風格與原 jaba 專案一致。

#### Scenario: 店家管理
- **WHEN** 超級管理員進入後台
- **THEN** 可以新增、編輯、啟用/停用店家

#### Scenario: 菜單管理
- **WHEN** 超級管理員選擇店家
- **THEN** 可以編輯菜單、上傳圖片辨識、查看差異預覽

#### Scenario: 群組管理
- **WHEN** 超級管理員查看群組列表
- **THEN** 可以查看所有群組、訂單、指定管理員

#### Scenario: 訂單管理
- **WHEN** 超級管理員選擇群組
- **THEN** 可以查看訂單、代理點餐、標記付款

#### Scenario: AI 對話管理
- **WHEN** 超級管理員在後台對話區輸入訊息
- **THEN** 可以透過 AI 對話進行管理操作

### Requirement: AI Prompt Management
系統 SHALL 提供 AI 提示詞編輯介面。

#### Scenario: 查看提示詞
- **WHEN** 超級管理員進入提示詞管理頁面
- **THEN** 系統顯示所有 AI 提示詞（群組點餐、管理員、個人偏好、菜單辨識）

#### Scenario: 編輯提示詞
- **WHEN** 超級管理員修改提示詞內容並儲存
- **THEN** 系統更新資料庫中的提示詞，立即生效

### Requirement: Order History Query
系統 SHALL 提供歷史訂單查詢功能。

#### Scenario: 群組歷史訂單
- **WHEN** 管理員選擇日期範圍
- **THEN** 系統顯示該群組在指定期間的所有訂單

#### Scenario: 訂單統計
- **WHEN** 管理員查看歷史訂單
- **THEN** 系統顯示訂單數量、總金額、熱門品項統計

