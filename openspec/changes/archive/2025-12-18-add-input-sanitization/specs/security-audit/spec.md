# Capability: security-audit

安全審計功能，提供輸入過濾和可疑行為記錄。

## ADDED Requirements

### Requirement: Input Sanitization

系統 MUST 過濾使用者輸入，偵測到可疑內容時靜默忽略並記錄。

#### Scenario: 長度限制
- Given 使用者輸入超過 200 字元的訊息
- When 系統處理該訊息
- Then 記錄到安全日誌
- And 系統不回應該訊息（靜默忽略）

#### Scenario: XML 標籤過濾
- Given 使用者輸入包含 `<script>` 或 `</system>` 等標籤
- When 系統處理該訊息
- Then 記錄到安全日誌
- And 系統不回應該訊息（靜默忽略）

#### Scenario: Markdown Code Block 過濾
- Given 使用者輸入包含 ` ``` ` 字串
- When 系統處理該訊息
- Then 記錄到安全日誌
- And 系統不回應該訊息（靜默忽略）

#### Scenario: 分隔線過濾
- Given 使用者輸入包含 `---` 或 `===` 連續字元
- When 系統處理該訊息
- Then 記錄到安全日誌
- And 系統不回應該訊息（靜默忽略）

#### Scenario: 正常訊息不記錄
- Given 使用者輸入正常的點餐訊息如「我要雞腿便當」
- When 系統處理該訊息
- Then 訊息原封不動傳送給 AI
- And 不記錄到安全日誌

### Requirement: Security Log Recording

系統 MUST 將可疑輸入完整記錄供超級管理員審查。

#### Scenario: 記錄完整資訊
- Given 偵測到可疑輸入
- When 系統記錄安全日誌
- Then 記錄包含:
  - 原始完整訊息（不截斷）
  - LINE user_id
  - 使用者顯示名稱
  - LINE group_id（如在群組中）
  - 觸發原因列表
  - 對話類型（group/personal）
  - 時間戳記

#### Scenario: 多重觸發原因
- Given 使用者輸入同時超過長度限制且包含 XML 標籤
- When 系統記錄安全日誌
- Then trigger_reasons 包含 `["length_exceeded", "xml_tags"]`

### Requirement: Security Log Query API

系統 MUST 提供 API 讓超級管理員查詢安全日誌。

#### Scenario: 列出最近日誌
- Given 超級管理員已登入
- When 呼叫 GET `/api/admin/security-logs`
- Then 回傳最近的安全日誌列表（預設 50 筆）

#### Scenario: 依使用者篩選
- Given 超級管理員已登入
- When 呼叫 GET `/api/admin/security-logs?line_user_id=U123`
- Then 僅回傳該使用者的安全日誌

#### Scenario: 依群組篩選
- Given 超級管理員已登入
- When 呼叫 GET `/api/admin/security-logs?line_group_id=C456`
- Then 僅回傳該群組的安全日誌

#### Scenario: 統計資訊
- Given 超級管理員已登入
- When 呼叫 GET `/api/admin/security-logs/stats`
- Then 回傳:
  - 總記錄數
  - 依觸發原因分類的統計
  - 最近 7 天的每日統計

### Requirement: Auto Ban on Threshold

系統 MUST 在使用者違規次數超過閾值時自動封鎖。

#### Scenario: 達到封鎖閾值
- Given 環境變數 SECURITY_BAN_THRESHOLD 設定為 5
- And 使用者已有 4 筆安全日誌記錄
- When 使用者再次觸發安全過濾
- Then 系統記錄第 5 筆安全日誌
- And 使用者 is_banned 設為 true
- And 記錄 banned_at 時間戳

#### Scenario: 封鎖後靜默忽略
- Given 使用者已被封鎖（is_banned = true）
- When 該使用者發送任何訊息
- Then 系統不回應任何訊息
- And 不記錄到對話歷史

#### Scenario: 未達閾值不封鎖
- Given 環境變數 SECURITY_BAN_THRESHOLD 設定為 5
- And 使用者已有 3 筆安全日誌記錄
- When 使用者再次觸發安全過濾
- Then 系統記錄第 4 筆安全日誌
- And 使用者 is_banned 保持 false
