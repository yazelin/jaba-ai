# line-bot Specification

## Purpose
TBD - created by archiving change add-group-admin-store-commands. Update Purpose after archive.
## Requirements
### Requirement: Group Admin Store Management
系統 SHALL 支援群組管理員在 LINE 群組中管理今日店家。

#### Scenario: 查詢今日店家
- **GIVEN** 使用者是群組管理員
- **AND** 群組目前非點餐中
- **WHEN** 管理員在群組中輸入「今日」
- **THEN** 系統顯示目前設定的今日店家列表
  - 若無設定則顯示「尚未設定今日店家」
- **AND** 系統顯示可用店家列表

#### Scenario: 直接輸入店名設定今日店家
- **GIVEN** 使用者是群組管理員
- **AND** 群組目前非點餐中
- **WHEN** 管理員在群組中直接輸入店名（或店名關鍵字）
- **THEN** 系統模糊匹配店家名稱
- **AND** 若只有一間匹配：清除原有今日店家並設定該店家
- **AND** 若多間匹配：列出匹配的店家供選擇

#### Scenario: 新增今日店家
- **GIVEN** 使用者是群組管理員
- **AND** 群組目前非點餐中
- **WHEN** 管理員在群組中輸入「加 XXX」
- **THEN** 系統新增指定店家至今日店家（不清除原有）
- **AND** 系統回應確認訊息

#### Scenario: 移除今日店家
- **GIVEN** 使用者是群組管理員
- **AND** 群組目前非點餐中
- **WHEN** 管理員在群組中輸入「移除 XXX」
- **THEN** 系統從今日店家移除指定店家
- **AND** 系統回應確認訊息

#### Scenario: 清除今日店家
- **GIVEN** 使用者是群組管理員
- **AND** 群組目前非點餐中
- **WHEN** 管理員在群組中輸入「清除」
- **THEN** 系統清除所有今日店家
- **AND** 系統回應確認訊息

#### Scenario: 店名找不到
- **WHEN** 管理員輸入的店名無法匹配系統中任何已存在的店家
- **THEN** 系統提示「找不到店家 XXX」
- **AND** 系統列出目前可用的店家供選擇

#### Scenario: 非管理員無權限
- **GIVEN** 使用者不是群組管理員
- **WHEN** 使用者輸入管理員指令
- **THEN** 系統不回應（靜默忽略）

#### Scenario: 管理員輸入不認識的內容
- **GIVEN** 使用者是群組管理員
- **AND** 群組目前非點餐中
- **AND** 輸入內容不是快捷指令（開單、菜單等）
- **AND** 輸入內容無法匹配任何店家
- **WHEN** 管理員輸入不認識的內容
- **THEN** 系統顯示管理員指令幫助

### Requirement: Admin Commands Only When Not Ordering
系統 SHALL 在非點餐狀態下才處理管理員店家指令。

#### Scenario: 非點餐中管理員指令
- **GIVEN** 群組目前非點餐中
- **WHEN** 管理員輸入店家管理指令
- **THEN** 系統應回應並執行操作

#### Scenario: 點餐中管理員指令
- **GIVEN** 群組目前點餐中
- **WHEN** 管理員輸入店家管理指令（如「今日店家」）
- **THEN** 系統不處理管理員指令
- **AND** 系統將輸入交給 AI 處理點餐

### Requirement: Quick Commands First
系統 SHALL 在管理員指令之前處理快捷指令。

#### Scenario: 快捷指令優先處理
- **WHEN** 任何人輸入「開單」或「菜單」等快捷指令
- **THEN** 系統優先執行快捷指令功能
- **AND** 不進入管理員指令處理流程

### Requirement: Admin Binding Command
系統 SHALL 支援群組成員透過群組代碼驗證綁定為群組管理員。

#### Scenario: 綁定成功
- **GIVEN** 群組已核准開通（存在 approved 的 group_application）
- **AND** 使用者不是群組管理員
- **WHEN** 使用者在群組中輸入「管理員 [正確代碼]」
- **THEN** 系統將該使用者加入群組管理員
- **AND** 系統回應綁定成功訊息及可用指令列表

#### Scenario: 代碼錯誤
- **WHEN** 使用者在群組中輸入「管理員 [錯誤代碼]」
- **THEN** 系統回應「代碼錯誤」
- **AND** 系統不透露申請是否存在

#### Scenario: 已是管理員
- **GIVEN** 使用者已是群組管理員
- **WHEN** 使用者在群組中輸入「管理員 [代碼]」
- **THEN** 系統回應「您已經是管理員」

#### Scenario: 群組未開通
- **GIVEN** 群組未開通（無 approved 的 group_application）
- **WHEN** 使用者在群組中輸入「管理員 [代碼]」
- **THEN** 系統回應「代碼錯誤」（不透露群組未開通）

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

### Requirement: Admin Help Message
系統 SHALL 在管理員指令幫助訊息中使用「群組代碼」術語。

#### Scenario: 幫助訊息文字
- **WHEN** 系統顯示管理員指令幫助
- **THEN** 解除管理員說明使用「代碼」而非「密碼」
- **AND** 綁定管理員說明使用「管理員 [代碼]」格式

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

### Requirement: LINE Webhook Integration
系統 SHALL 整合 LINE Webhook 接收和處理訊息。

#### Scenario: Webhook 驗證
- **WHEN** LINE Platform 發送 Webhook
- **THEN** 系統驗證 X-Line-Signature 簽章

#### Scenario: 文字訊息處理
- **WHEN** 收到文字訊息
- **THEN** 系統根據訊息內容和群組狀態進行處理

#### Scenario: Leave 事件處理
- **WHEN** Bot 被踢出群組
- **THEN** 系統更新群組狀態

### Requirement: Group Ordering Session
系統 SHALL 管理群組點餐 Session。

#### Scenario: 開始點餐
- **WHEN** 使用者在已啟用群組中說「開單」
- **THEN** 系統建立 Session 並顯示今日菜單

#### Scenario: 點餐處理
- **WHEN** Session 進行中且使用者發送訊息
- **THEN** AI 解析訊息並執行訂單操作

#### Scenario: 結束點餐
- **WHEN** 使用者說「收單」
- **THEN** 系統結束 Session 並顯示訂單摘要

### Requirement: Order Operations
系統 SHALL 支援透過自然語言進行訂單操作。

#### Scenario: 建立訂單
- **WHEN** 使用者說「我要雞腿便當」
- **THEN** AI 解析並建立訂單

#### Scenario: 修改訂單
- **WHEN** 使用者說「改排骨」
- **THEN** AI 解析並修改使用者的訂單

#### Scenario: 取消訂單
- **WHEN** 使用者說「不要了」
- **THEN** AI 解析並取消使用者的訂單

#### Scenario: 跟單
- **WHEN** 使用者說「+1」或「我也要」
- **THEN** AI 複製最近的訂單給該使用者

### Requirement: Personal Preference Setting
系統 SHALL 支援 1v1 聊天中設定個人偏好。

#### Scenario: 設定稱呼
- **WHEN** 使用者在 1v1 說「叫我小明」
- **THEN** 系統儲存使用者的偏好稱呼

#### Scenario: 設定飲食偏好
- **WHEN** 使用者在 1v1 說「我不吃辣」
- **THEN** 系統儲存使用者的飲食限制

#### Scenario: 套用偏好
- **WHEN** 使用者在群組點餐
- **THEN** AI 參考個人偏好進行提醒

### Requirement: Status Query
系統 SHALL 支援使用者查詢群組啟用狀態。

#### Scenario: 查詢狀態
- **WHEN** 使用者輸入「jaba」或相關指令
- **THEN** 系統回應群組的啟用狀態

#### Scenario: 未啟用提示
- **WHEN** 使用者在未啟用群組嘗試點餐
- **THEN** 系統提示群組尚未啟用，需申請

