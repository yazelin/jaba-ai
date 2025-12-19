## ADDED Requirements

### Requirement: Admin Binding Command
系統 SHALL 支援群組成員透過密碼驗證綁定為群組管理員。

#### Scenario: 綁定成功
- **GIVEN** 群組已核准開通（存在 approved 的 group_application）
- **AND** 使用者不是群組管理員
- **WHEN** 使用者在群組中輸入「管理員 [正確密碼]」
- **THEN** 系統將該使用者加入群組管理員
- **AND** 系統回應綁定成功訊息及可用指令列表

#### Scenario: 密碼錯誤
- **WHEN** 使用者在群組中輸入「管理員 [錯誤密碼]」
- **THEN** 系統回應「密碼錯誤」
- **AND** 系統不透露申請是否存在

#### Scenario: 已是管理員
- **GIVEN** 使用者已是群組管理員
- **WHEN** 使用者在群組中輸入「管理員 [密碼]」
- **THEN** 系統回應「您已經是管理員」

#### Scenario: 群組未開通
- **GIVEN** 群組未開通（無 approved 的 group_application）
- **WHEN** 使用者在群組中輸入「管理員 [密碼]」
- **THEN** 系統回應「密碼錯誤」（不透露群組未開通）

### Requirement: Application Page Description
申請頁面 SHALL 說明管理密碼的完整用途。

#### Scenario: 密碼說明
- **WHEN** 使用者查看申請頁面的管理密碼欄位
- **THEN** 說明文字包含「此密碼用於登入管理後台，也可在群組中輸入『管理員 [密碼]』綁定管理員身份」
