## REMOVED Requirements

### Requirement: Admin Commands Only When Not Ordering
**Reason**: 點餐中管理員打店名會被送進 AI 當成點餐，造成「舊單卡住新的一天」（03-02、04-14、08-13、11-02）。
**Migration**: 由「Admin Commands During Ordering」取代，管理員指令在點餐中也生效。

## ADDED Requirements

### Requirement: Admin Commands During Ordering
系統 SHALL 不論是否點餐中都處理管理員店家指令。

#### Scenario: 點餐中輸入店名且尚無訂單
- **GIVEN** 群組今天的單進行中且沒有任何訂單
- **WHEN** 管理員輸入店名
- **THEN** 系統換成該店家並回應今日菜單

#### Scenario: 點餐中輸入店名且已有訂單
- **GIVEN** 群組今天的單進行中且已有訂單
- **WHEN** 管理員輸入其他店名
- **THEN** 系統不換店家
- **AND** 系統回應目前訂單筆數，並提示要換店請先結單

### Requirement: Store Selection Opens Session
系統 SHALL 在管理員設定今日店家時同時開單。

#### Scenario: 設定店家即開單
- **GIVEN** 群組目前沒有進行中的單
- **WHEN** 管理員輸入店名或「XX菜單」
- **THEN** 系統設定今日店家、開單並顯示菜單

### Requirement: Stale Session Auto Close
系統 SHALL 自動結束不是今天開的單，並在每天固定時間結束當天的單。

#### Scenario: 收到訊息時舊單自動結束
- **GIVEN** 群組有進行中的單，開單日期早於今天
- **WHEN** 群組收到任何訊息
- **THEN** 系統先結束該單，再處理這則訊息

#### Scenario: 每日排程結單
- **GIVEN** 時間到達每日結單時間
- **WHEN** 排程執行
- **THEN** 系統結束當天所有進行中的單
- **AND** 沒有訂單的單直接刪除

### Requirement: Message Normalization
系統 SHALL 在比對指令前正規化訊息。

#### Scenario: 去掉提及呷爸的標記
- **WHEN** 使用者輸入「@jaba 呷爸 菜單」
- **THEN** 系統以「菜單」處理

#### Scenario: 指令常見變體
- **WHEN** 使用者輸入「請開單」、「help」或管理員輸入「管理員1234」
- **THEN** 系統分別視為「開單」、幫助、「管理員 1234」

### Requirement: Rule Based Order Parsing
系統 SHALL 以程式解析固定格式的點餐訊息，不經過 AI。

#### Scenario: 品項加數量
- **GIVEN** 點餐進行中，今日菜單有「炸排骨飯」
- **WHEN** 使用者輸入「炸排骨+1」
- **THEN** 系統為該使用者加入炸排骨飯 1 份

#### Scenario: 代訂
- **WHEN** 使用者輸入「椒鹽雞塊*3 (老闆)」
- **THEN** 系統在該使用者名下加入椒鹽雞塊 3 份，備註「老闆」

#### Scenario: 多品項
- **WHEN** 使用者輸入兩行「黯然飯*1」與「銷魂飯*1」
- **THEN** 系統加入兩個品項各 1 份

#### Scenario: 減少數量
- **GIVEN** 使用者已點蔥油雞 4 份
- **WHEN** 使用者輸入「少一個蔥油雞」
- **THEN** 蔥油雞變為 3 份

#### Scenario: 品項有多個候選
- **WHEN** 使用者輸入的品項對應到多個菜單品項
- **THEN** 系統回一題編號選擇，不寫入訂單

### Requirement: Default Item Options
系統 SHALL 在使用者沒有指定時使用品項的預設選項，不追問。

#### Scenario: 沒講飯或麵
- **WHEN** 使用者輸入「玫瑰油雞飯」，菜單品項有飯、麵兩個選項
- **THEN** 系統以飯建立訂單
- **AND** 確認行寫出所選的選項

### Requirement: Order Confirmation From Database
系統 SHALL 在訂單變動後，以資料庫內容產生確認訊息。

#### Scenario: 點餐後回覆
- **WHEN** 使用者的訂單有變動
- **THEN** 系統回覆該使用者目前的品項、數量與小計
- **AND** 回覆內容取自資料庫，不取自 AI 產生的文字
- **AND** 不附上全體訂單摘要

### Requirement: Orders Before Session Opens
系統 SHALL 不遺漏開單前送出的點餐。

#### Scenario: 已設定店家但未開單
- **GIVEN** 今日店家已設定，沒有進行中的單
- **WHEN** 使用者輸入可解析的點餐訊息
- **THEN** 系統自動開單並寫入訂單

#### Scenario: 未設定店家
- **GIVEN** 今日店家未設定
- **WHEN** 使用者輸入帶數量記號的點餐訊息
- **THEN** 系統提醒尚未選店家（同一天只提醒一次）並暫存訊息
- **AND** 開單時系統以暫存訊息補單並公布結果

### Requirement: Serialized Group Processing
系統 SHALL 同一群組一次只處理一則訊息。

#### Scenario: 同時多人點餐
- **WHEN** 同一群組幾乎同時收到多則點餐訊息
- **THEN** 系統依收到順序逐一處理，每則都寫入訂單

### Requirement: Restated Orders Not Duplicated
系統 SHALL 不重複加入與本人現有訂單完全相同的點餐。

#### Scenario: 重傳同一則
- **GIVEN** 使用者已點古早味排骨 1 份
- **WHEN** 使用者再傳一次「古早味排骨飯*1」
- **THEN** 訂單維持 1 份
- **AND** 系統提醒要多一份請打「再加一個」

#### Scenario: 數量不同視為追加
- **GIVEN** 使用者已點銷魂飯 1 份
- **WHEN** 使用者輸入「銷魂飯*3」
- **THEN** 銷魂飯變為 4 份，確認行顯示總數

#### Scenario: 明講追加
- **WHEN** 使用者輸入「再加一個黯然飯」
- **THEN** 系統一定追加

### Requirement: Admin Price Update
系統 SHALL 讓群組管理員在群組中修改今日菜單價格。

#### Scenario: 改價
- **WHEN** 管理員輸入「改價 銷魂飯 80」
- **THEN** 菜單價格更新
- **AND** 今天進行中的訂單裡的該品項一起改價

### Requirement: Payment Commands
系統 SHALL 讓群組管理員在群組中標記付款與查詢未付款。

#### Scenario: 標記已付
- **WHEN** 管理員輸入「已付 同事A」
- **THEN** 最近一次點餐中同事A的訂單標記為已付
- **AND** 系統列出還沒付的人與金額

#### Scenario: 結單提示
- **WHEN** 點餐結束
- **THEN** 摘要標示已付款的人，並提示收款指令

### Requirement: AI Failure Handling
系統 SHALL 在 AI 呼叫失敗時回覆易懂的訊息，不顯示原始錯誤。

#### Scenario: AI 登入過期
- **WHEN** AI 呼叫回傳登入過期等錯誤
- **THEN** 使用者收到「AI 暫時連不上，固定格式的點餐還是可以用」
- **AND** 原始錯誤只記錄在 log
- **AND** 若設定了系統管理員，推播通知（一小時最多一次）

## MODIFIED Requirements

### Requirement: Group Ordering Session
系統 SHALL 管理群組點餐 Session。

#### Scenario: 開始點餐
- **WHEN** 使用者在已啟用群組中說「開單」或「請開單」，或管理員設定今日店家
- **THEN** 系統建立 Session 並顯示今日菜單

#### Scenario: 點餐處理
- **WHEN** Session 進行中且使用者發送訊息
- **THEN** 系統先以規則解析，解析不了才交給 AI，最後由程式執行訂單操作

#### Scenario: 結束點餐
- **WHEN** 使用者說「收單」或「結單」
- **THEN** 系統結束 Session 並顯示訂單摘要

### Requirement: Order Operations
系統 SHALL 支援透過自然語言進行訂單操作，且訂單只由程式寫入。

#### Scenario: 建立訂單
- **WHEN** 使用者說「我要雞腿便當」
- **THEN** 系統解析並建立訂單

#### Scenario: 修改訂單
- **WHEN** 使用者說「改排骨」
- **THEN** 系統解析並修改使用者的訂單

#### Scenario: 取消訂單
- **WHEN** 使用者說「不要了」
- **THEN** 系統取消使用者的訂單

#### Scenario: 未明確取消時不刪整筆訂單
- **WHEN** AI 回傳取消整筆訂單，但使用者訊息沒有取消、不要、算了等字
- **THEN** 系統不執行取消

#### Scenario: 重列整份訂單
- **WHEN** 使用者把自己的整份訂單重新列一次
- **THEN** 系統以該清單取代原訂單，不重複追加

#### Scenario: 跟單
- **WHEN** 使用者說「+1」或「我也要」且沒有指定品項
- **THEN** 系統複製本次點餐最近一筆訂單給該使用者
