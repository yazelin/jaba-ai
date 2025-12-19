# API 文件

## 概述

Jaba AI 提供 RESTful API 和 WebSocket (Socket.IO) 兩種介面。

- **RESTful API**：用於資料查詢和操作
- **Socket.IO**：用於即時訊息推送

## 認證方式

### 超級管理員 API (`/api/admin/*`)

使用 Token 認證，登入後取得 token，之後的請求需在 Header 中帶入：

```
Authorization: Bearer <token>
```

### LINE 管理員 API (`/api/line-admin/*`)

使用群組代碼認證，登入後取得可管理的群組列表。

### 公開 API

部分 API 不需要認證：
- `/api/public/*` - 菜單查詢
- `/api/line-admin/applications` - 提交申請
- `/api/board/*` - 看板資料

---

## 超級管理員 API

### 認證

#### POST /api/admin/verify
驗證超級管理員帳號密碼。

**Request:**
```json
{
  "username": "admin",
  "password": "password123"
}
```

**Response:**
```json
{
  "success": true,
  "token": "xxxxx",
  "username": "admin"
}
```

---

### 店家管理

#### GET /api/admin/stores
取得所有店家。

**Query Parameters:**
- `scope` (optional): 篩選 `global` 或 `group`
- `group_code` (optional): 篩選指定群組代碼

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "好吃便當",
    "phone": "02-1234-5678",
    "address": "台北市...",
    "description": "...",
    "note": "...",
    "is_active": true,
    "scope": "global",
    "group_code": null,
    "created_by_type": "admin"
  }
]
```

#### POST /api/admin/stores
建立店家。

**Request:**
```json
{
  "name": "好吃便當",
  "phone": "02-1234-5678",
  "address": "台北市...",
  "scope": "global",
  "group_code": null
}
```

#### PUT /api/admin/stores/{store_id}
更新店家。

**Request:**
```json
{
  "name": "新名稱",
  "is_active": false
}
```

#### DELETE /api/admin/stores/{store_id}
刪除店家。

---

### 菜單管理

#### POST /api/admin/menu/recognize
辨識菜單圖片（不指定店家）。

**Request:** `multipart/form-data`
- `file`: 圖片檔案

**Response:**
```json
{
  "categories": [
    {
      "name": "便當類",
      "items": [
        {
          "name": "雞腿便當",
          "price": 85,
          "variants": [],
          "description": ""
        }
      ]
    }
  ]
}
```

#### POST /api/admin/stores/{store_id}/menu/recognize
辨識菜單圖片並與現有菜單比對。

**Response:**
```json
{
  "recognized_menu": { ... },
  "existing_menu": { ... },
  "diff": {
    "added": [...],
    "removed": [...],
    "modified": [...]
  }
}
```

#### POST /api/admin/stores/{store_id}/menu
儲存菜單（完整覆蓋）。

**Request:**
```json
{
  "categories": [
    {
      "name": "便當類",
      "items": [
        {
          "name": "雞腿便當",
          "price": 85
        }
      ]
    }
  ]
}
```

#### POST /api/admin/stores/{store_id}/menu/save
儲存菜單（差異模式）。

**Request:**
```json
{
  "diff_mode": true,
  "apply_items": [
    {"name": "雞腿便當", "price": 90, "category": "便當類"}
  ],
  "remove_items": ["舊品項名稱"]
}
```

---

### 群組管理

#### GET /api/admin/groups
取得所有群組。

**Response:**
```json
[
  {
    "id": "uuid",
    "line_group_id": "Cxxx",
    "name": "公司午餐群",
    "status": "active",
    "activated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### GET /api/admin/groups/{group_id}
取得群組詳情（含管理員列表）。

#### POST /api/admin/groups/{group_id}/activate
啟用群組。

#### POST /api/admin/groups/{group_id}/suspend
停用群組。

---

### 申請審核

#### GET /api/admin/applications
取得申請列表。

**Query Parameters:**
- `status` (optional): `pending` | `approved` | `rejected`

**Response:**
```json
[
  {
    "id": "uuid",
    "line_group_id": "Cxxx",
    "group_name": "公司午餐群",
    "contact_info": "小明 0912-345-678",
    "group_code": "abc123",
    "status": "pending",
    "created_at": "2024-01-01T00:00:00Z",
    "reviewed_at": null
  }
]
```

#### POST /api/admin/applications/{app_id}/review
審核申請。

**Request:**
```json
{
  "status": "approved",
  "note": "審核通過"
}
```

---

### 訂單管理

#### GET /api/admin/groups/{group_id}/orders
取得群組訂單。

**Query Parameters:**
- `all_sessions` (optional): `true` 取得今日所有 session

**Response:**
```json
[
  {
    "session_id": "uuid",
    "status": "ordering",
    "started_at": "2024-01-01T12:00:00Z",
    "orders": [
      {
        "id": "uuid",
        "user_id": "uuid",
        "display_name": "小明",
        "total": 85,
        "payment_status": "unpaid",
        "items": [
          {
            "name": "雞腿便當",
            "quantity": 1,
            "subtotal": 85
          }
        ]
      }
    ]
  }
]
```

#### POST /api/admin/orders/{order_id}/mark-paid
標記訂單已付款。

#### DELETE /api/admin/orders/{order_id}
刪除訂單。

---

### 代理點餐

#### POST /api/admin/groups/{group_id}/proxy-orders
代理建立訂單。

**Request:**
```json
{
  "user_id": "uuid",
  "items": [
    {
      "name": "雞腿便當",
      "quantity": 1,
      "note": "不要辣"
    }
  ]
}
```

#### PUT /api/admin/groups/{group_id}/proxy-orders/{order_id}
代理修改訂單。

---

### AI 提示詞管理

#### GET /api/admin/prompts
取得所有提示詞。

**Response:**
```json
[
  {
    "id": "uuid",
    "name": "group_ordering",
    "content": "你是呷爸...",
    "updated_at": "2024-01-01T00:00:00Z"
  }
]
```

#### PUT /api/admin/prompts/{name}
更新提示詞。

**Request:**
```json
{
  "content": "新的提示詞內容..."
}
```

---

## LINE 管理員 API

### 認證

#### POST /api/line-admin/login
LINE 管理員登入。

**Request:**
```json
{
  "password": "群組代碼"
}
```

**Response:**
```json
{
  "success": true,
  "groups": [
    {
      "group_id": "uuid",
      "group_name": "公司午餐群"
    }
  ]
}
```

---

### 群組申請

#### POST /api/line-admin/applications
提交群組申請。

**Request:**
```json
{
  "line_group_id": "Cxxx",
  "group_name": "公司午餐群",
  "contact_info": "小明 0912-345-678",
  "group_code": "mycode123"
}
```

#### GET /api/line-admin/applications/{line_group_id}
查詢申請狀態（以 LINE 群組 ID）。

#### GET /api/line-admin/applications/by-code/{group_code}
查詢申請狀態（以群組代碼）。

---

### 群組管理

#### GET /api/line-admin/groups/{group_id}
取得群組資訊。

#### GET /api/line-admin/groups/{group_id}/orders
取得群組訂單。

#### GET /api/line-admin/groups/{group_id}/today-stores
取得今日店家。

#### POST /api/line-admin/groups/{group_id}/today-stores
設定今日店家。

**Request:**
```json
{
  "store_ids": ["uuid1", "uuid2"]
}
```

---

### 店家管理（群組專屬）

#### GET /api/line-admin/stores/by-code/{group_code}
取得群組可用店家（全局 + 群組專屬）。

#### POST /api/line-admin/stores/by-code/{group_code}
建立群組專屬店家。

**Request:**
```json
{
  "name": "隔壁便當店",
  "phone": "02-9999-9999"
}
```

#### PUT /api/line-admin/stores/by-code/{group_code}/{store_id}
更新群組店家（僅能更新 scope=group 的店家）。

#### DELETE /api/line-admin/stores/by-code/{group_code}/{store_id}
刪除群組店家。

---

### 菜單管理（群組專屬）

#### GET /api/line-admin/stores/by-code/{group_code}/{store_id}/menu
取得店家菜單。

#### POST /api/line-admin/menu/recognize
辨識菜單圖片。

#### POST /api/line-admin/stores/by-code/{group_code}/{store_id}/menu
儲存菜單（完整覆蓋）。

#### POST /api/line-admin/stores/by-code/{group_code}/{store_id}/menu/save
儲存菜單（差異模式）。

---

## 公開 API

### 菜單查詢

#### GET /api/public/stores/{store_id}/menu
取得店家菜單（公開）。

---

### 看板 API

#### GET /api/board/groups/{group_id}/status
取得群組點餐狀態。

**Response:**
```json
{
  "is_ordering": true,
  "session_id": "uuid",
  "today_stores": [
    {
      "store_id": "uuid",
      "store_name": "好吃便當"
    }
  ]
}
```

#### GET /api/board/groups/{group_id}/orders
取得群組當前訂單。

---

## LINE Webhook

### POST /api/webhook/line
LINE Webhook 接收端點。

由 LINE Platform 自動呼叫，處理：
- 文字訊息
- 加入/離開群組事件
- Postback 事件

---

## Socket.IO 事件

### 連線

```javascript
const socket = io('http://localhost:8089');

// 加入群組房間（看板）
socket.emit('join_board', { group_id: 'uuid' });

// 加入所有群組房間（看板選擇 "全部"）
socket.emit('join_board', { group_id: 'all' });

// 加入超管房間
socket.emit('join_admin');

// 離開群組房間
socket.emit('leave_board', { group_id: 'uuid' });
```

### 事件監聽

#### order_update
訂單更新事件。

```javascript
socket.on('order_update', (data) => {
  // data: { group_id, action, user_id, display_name }
  // action: 'created' | 'updated' | 'cancelled'
});
```

#### chat_message
聊天訊息事件。

```javascript
socket.on('chat_message', (data) => {
  // data: { group_id, user_id, display_name, role, content }
  // role: 'user' | 'assistant'
});
```

#### session_status
點餐狀態變更事件。

```javascript
socket.on('session_status', (data) => {
  // data: { group_id, session_id, status, started_by/ended_by }
  // status: 'ordering' | 'ended'
});
```

#### payment_update
付款狀態變更事件。

```javascript
socket.on('payment_update', (data) => {
  // data: { group_id, order_id, payment_status }
});
```

#### store_change
今日店家變更事件。

```javascript
socket.on('store_change', (data) => {
  // data: { group_id, action, store_name }
  // action: 'set' | 'add' | 'remove' | 'clear'
});
```

#### application_update
群組申請狀態變更事件（超管房間）。

```javascript
socket.on('application_update', (data) => {
  // data: { application_id, status, group_name }
  // status: 'pending' | 'approved' | 'rejected'
});
```

#### group_update
群組成員變更事件（超管房間）。

```javascript
socket.on('group_update', (data) => {
  // data: { group_id, action }
  // action: 'member_added'
});
```

---

## 錯誤回應

所有 API 錯誤回應格式：

```json
{
  "detail": "錯誤訊息"
}
```

常見 HTTP 狀態碼：
- `400` - 請求參數錯誤
- `401` - 未認證或 Token 無效
- `403` - 權限不足
- `404` - 資源不存在
- `500` - 伺服器錯誤
