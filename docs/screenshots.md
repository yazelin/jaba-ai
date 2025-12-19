# 系統截圖

本文件展示 Jaba AI 各功能模組的操作畫面。

## 目錄

- [訂餐看板](#訂餐看板)
- [LINE 群組管理](#line-群組管理)
- [超級管理員後台](#超級管理員後台)

---

## 訂餐看板

即時訂餐看板，顯示今日店家、美食評論區、訂單列表和統計。

### 看板主頁

![訂餐看板](../demo/01-board-main-dashboard.png)

### 群組申請

透過看板頁面申請開通新群組。

![群組申請](../demo/02-board-group-application.png)

---

## LINE 群組管理

LINE 群組管理員可透過此介面管理店家、菜單和訂單。

### 管理主頁

顯示店家管理、今日店家設定、訂單統計等功能。

![LINE 管理主頁](../demo/03-line-admin-dashboard.png)

### 設定今日店家

選擇今日可點餐的店家。

![設定今日店家](../demo/04-line-admin-set-today-store.png)

### 菜單上傳與 AI 辨識

#### 1. 上傳菜單圖片

拖放或點擊上傳菜單圖片。

![菜單上傳](../demo/05-line-admin-menu-upload-dropzone.png)

#### 2. 圖片預覽

確認上傳的菜單圖片。

![菜單預覽](../demo/06-line-admin-menu-upload-preview.png)

#### 3. AI 辨識中

AI 自動辨識菜單品項和價格。

![AI 辨識中](../demo/07-line-admin-menu-ai-processing.png)

#### 4. 辨識結果

AI 辨識完成後顯示新增/修改/刪除的品項差異比較，以及店家資訊更新建議。

![AI 辨識結果](../demo/08-line-admin-menu-ai-result.png)

### 菜單編輯

手動編輯菜單品項、價格和說明。

![菜單編輯](../demo/09-line-admin-menu-edit.png)

---

## 超級管理員後台

超級管理員可管理所有群組、店家、使用者和系統設定。

### 訂單管理

查看和管理群組訂單，包含訂單統計和品項統計。右下角有「呷爸助手」對話視窗。

![訂單管理](../demo/10-admin-order-management.png)

### 店家管理

管理所有店家和菜單，支援上傳菜單圖片進行 AI 辨識。

![店家管理](../demo/11-admin-store-management.png)

### 店家菜單編輯

編輯店家菜單品項、價格、說明，以及店家資訊（名稱、電話、地址、營業時間）。

![店家菜單編輯](../demo/12-admin-store-menu-edit.png)

### 群組管理

審核群組申請、管理群組狀態（啟用/凍結/刪除）。

![群組管理](../demo/13-admin-group-management.png)

### 使用者管理

查看和管理使用者，支援封鎖功能。

![使用者管理](../demo/14-admin-user-management.png)

### 違規記錄

記錄 Prompt Injection 等安全違規事件，顯示今日/本週/總違規數統計。

![違規記錄](../demo/15-admin-security-logs.png)

### AI 日誌

查看 AI 對話日誌，包含完整的輸入 prompt 和原始回應（含思考過程）。

#### 日誌列表

顯示時間、使用者、群組、模型、訊息摘要、耗時和狀態。

![AI 日誌列表](../demo/16-admin-ai-logs-list.png)

#### 日誌詳情 - 輸入 Prompt

展示完整的系統 prompt、對話歷史和使用者訊息。

![AI 日誌詳情 - Prompt](../demo/17-admin-ai-logs-detail-prompt.png)

#### 日誌詳情 - AI 回應

展示 AI 原始回應（含思考過程）、解析後訊息和解析後動作。

![AI 日誌詳情 - 回應](../demo/18-admin-ai-logs-detail-response.png)

### 系統設定

管理 AI 提示詞和系統維護，顯示 LINE Bot 連線狀態。

![系統設定](../demo/19-admin-system-settings.png)

### AI 提示詞編輯

編輯各類 AI 提示詞（群組點餐、菜單辨識、個人偏好等）。

![AI 提示詞編輯](../demo/20-admin-ai-prompt-editor.png)
