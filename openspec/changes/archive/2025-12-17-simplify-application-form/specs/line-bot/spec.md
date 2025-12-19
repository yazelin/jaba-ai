# line-bot Spec Delta

## ADDED Requirements

### Requirement: Admin Help Message
系統 SHALL 在管理員指令幫助訊息中使用「群組代碼」術語。

#### Scenario: 幫助訊息文字
- **WHEN** 系統顯示管理員指令幫助
- **THEN** 解除管理員說明使用「代碼」而非「密碼」
- **AND** 綁定管理員說明使用「管理員 [代碼]」格式
