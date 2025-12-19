# store-management Specification

## Purpose
TBD - created by archiving change add-hybrid-store-menu-management. Update Purpose after archive.
## Requirements
### Requirement: Hybrid Store Scope
系統 SHALL 支援兩種店家層級：全局店家 (global) 和群組店家 (group)。

#### Scenario: 全局店家建立
- **GIVEN** 使用者為超級管理員
- **WHEN** 建立店家時選擇 scope=global
- **THEN** 店家對所有群組可見
- **AND** 只有超管可編輯此店家

#### Scenario: 群組店家建立
- **GIVEN** 使用者為 LINE 管理員
- **WHEN** 建立店家
- **THEN** 店家自動設為 scope=group
- **AND** 自動關聯使用者的 group_code
- **AND** 只有相同 group_code 的群組可見此店家

#### Scenario: 店家列表篩選
- **GIVEN** LINE 管理員的 group_code 為 "team123"
- **WHEN** 請求店家列表
- **THEN** 返回所有 scope=global 的店家
- **AND** 返回所有 scope=group 且 group_code="team123" 的店家
- **AND** 不返回其他 group_code 的群組店家

### Requirement: Store Edit Permission
系統 SHALL 限制店家編輯權限，防止 LINE 管理員覆蓋超管建立的店家。

#### Scenario: LINE 管編輯群組店家
- **GIVEN** LINE 管理員的 group_code 為 "team123"
- **AND** 店家 scope=group 且 group_code="team123"
- **WHEN** LINE 管嘗試編輯店家
- **THEN** 允許編輯

#### Scenario: LINE 管編輯全局店家
- **GIVEN** LINE 管理員嘗試編輯 scope=global 的店家
- **WHEN** 送出編輯請求
- **THEN** 系統拒絕並返回 403 Forbidden
- **AND** 顯示「無權限編輯全局店家」

#### Scenario: LINE 管編輯其他群組店家
- **GIVEN** LINE 管理員的 group_code 為 "team123"
- **AND** 店家 scope=group 且 group_code="team456"
- **WHEN** LINE 管嘗試編輯店家
- **THEN** 系統拒絕並返回 403 Forbidden

#### Scenario: 超管編輯任意店家
- **GIVEN** 使用者為超級管理員
- **WHEN** 編輯任何店家
- **THEN** 允許編輯

### Requirement: Menu Diff Preview
系統 SHALL 支援菜單差異預覽功能，在上傳新菜單時顯示變更內容。

#### Scenario: 菜單差異比對
- **GIVEN** 店家已有現存菜單
- **WHEN** 上傳新菜單（圖片或手動輸入）
- **THEN** 系統比對新舊菜單
- **AND** 返回差異結果包含：added, modified, unchanged, removed

#### Scenario: 新品項識別
- **GIVEN** 新菜單包含現有菜單沒有的品項
- **WHEN** 執行差異比對
- **THEN** 該品項出現在 added 列表

#### Scenario: 品項修改識別
- **GIVEN** 新菜單包含名稱相同但價格不同的品項
- **WHEN** 執行差異比對
- **THEN** 該品項出現在 modified 列表
- **AND** 包含變更詳情（如：價格 $40 → $45）

#### Scenario: 品項移除識別
- **GIVEN** 現有菜單包含新菜單沒有的品項
- **WHEN** 執行差異比對
- **THEN** 該品項出現在 removed 列表

### Requirement: Selective Menu Update
系統 SHALL 支援選擇性菜單更新，使用者可選擇要套用哪些變更。

#### Scenario: 差異模式儲存
- **GIVEN** 使用者在差異預覽中勾選部分品項
- **WHEN** 使用 diff_mode=true 儲存
- **THEN** 只套用勾選的變更
- **AND** 保留未勾選的現有品項

#### Scenario: 完整覆蓋模式
- **GIVEN** 使用者選擇完整覆蓋
- **WHEN** 使用 diff_mode=false 儲存
- **THEN** 新菜單完全取代舊菜單

#### Scenario: 刪除品項
- **GIVEN** 使用者在差異預覽中勾選 removed 品項
- **WHEN** 儲存時包含 remove_items
- **THEN** 系統從菜單中移除指定品項

### Requirement: Store Management UI for LINE Admin
系統 SHALL 在 LINE 管理員頁面提供店家管理介面。

#### Scenario: 店家列表顯示
- **WHEN** LINE 管理員進入店家管理頁面
- **THEN** 顯示可用店家列表
- **AND** 全局店家標示 [全局]
- **AND** 群組店家標示 [群組專屬]
- **AND** 全局店家不顯示編輯按鈕

#### Scenario: 新增群組店家
- **WHEN** LINE 管理員點擊「新增店家」
- **THEN** 顯示店家表單
- **AND** 填寫後建立 scope=group 的店家

#### Scenario: 菜單上傳與預覽
- **WHEN** LINE 管理員上傳菜單圖片
- **THEN** 系統辨識菜單內容
- **AND** 顯示差異預覽（若已有菜單）
- **AND** 使用者可選擇套用項目

