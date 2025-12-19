"""AI 聊天 API 路由"""
from typing import Optional, List
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.services import AiService, CacheService
from app.repositories import (
    StoreRepository,
    GroupTodayStoreRepository,
    GroupRepository,
    AiPromptRepository,
)
from app.broadcast import commit_and_notify, emit_store_change

router = APIRouter(prefix="/api", tags=["chat"])


class ChatMessage(BaseModel):
    role: str  # user or assistant
    content: str


class ChatRequest(BaseModel):
    message: str
    username: Optional[str] = None
    is_manager: bool = False
    group_id: Optional[str] = None  # 選擇的群組 ID（用於設定今日店家等操作）
    history: Optional[List[ChatMessage]] = None


class ChatResponse(BaseModel):
    message: str
    actions: list = []


@router.post("/chat", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """AI 聊天 API"""
    ai_service = AiService()

    # 根據模式取得提示詞
    if request.is_manager:
        prompt_name = "manager_prompt"
    else:
        prompt_name = "group_ordering"

    # 從快取或資料庫取得提示詞
    system_prompt = CacheService.get_prompt(prompt_name)
    if not system_prompt:
        prompt_repo = AiPromptRepository(db)
        prompt = await prompt_repo.get_by_name(prompt_name)
        if prompt:
            system_prompt = prompt.content
            CacheService.set_prompt(prompt_name, system_prompt)
        else:
            # 使用預設提示詞
            system_prompt = _get_default_prompt(prompt_name)

    # 建立上下文
    context = await _build_context(db, request.username, request.is_manager, request.group_id)

    # 轉換歷史格式
    history = None
    if request.history:
        history = [{"role": msg.role, "content": msg.content} for msg in request.history]

    # 呼叫 AI
    result = await ai_service.chat(
        message=request.message,
        system_prompt=system_prompt,
        context=context,
        history=history,
    )

    # 執行動作（如果有的話）
    if result.get("actions"):
        await _execute_actions(db, result["actions"])
        await commit_and_notify(db)

    return ChatResponse(
        message=result.get("message", ""),
        actions=result.get("actions", []),
    )


async def _build_context(
    db: AsyncSession,
    username: Optional[str],
    is_manager: bool,
    group_id: Optional[str] = None,
) -> dict:
    """建立 AI 對話上下文"""
    context = {
        "username": username or "使用者",
        "is_manager": is_manager,
    }

    # 取得店家列表
    store_repo = StoreRepository(db)
    stores = await store_repo.get_active_stores()
    context["stores"] = [
        {"id": str(s.id), "name": s.name, "phone": s.phone}
        for s in stores
    ]

    # 如果有指定群組，加入群組資訊
    if group_id:
        context["selected_group_id"] = group_id

    # 如果是管理員，取得群組列表
    if is_manager:
        group_repo = GroupRepository(db)
        groups = await group_repo.get_all()
        context["groups"] = [
            {"id": str(g.id), "name": g.name or f"群組 {g.line_group_id[-8:]}"}
            for g in groups
        ]

    return context


async def _execute_actions(db: AsyncSession, actions: list) -> None:
    """執行 AI 回傳的動作"""
    from app.services import CacheService

    for action in actions:
        action_type = action.get("type")
        data = action.get("data", {})

        if action_type == "set_today_store":
            # 設定今日店家（會清除其他店家）
            store_id = data.get("store_id")
            group_id = data.get("group_id")
            if store_id and group_id:
                repo = GroupTodayStoreRepository(db)
                await repo.clear_today_stores(UUID(group_id))
                await repo.set_today_store(UUID(group_id), UUID(store_id))
                CacheService.clear_today_stores(group_id)
                # 廣播今日店家變更
                await emit_store_change(group_id, {
                    "group_id": group_id,
                    "action": "set",
                })

        elif action_type == "add_today_store":
            # 新增今日店家（不清除其他店家，可多家）
            store_id = data.get("store_id")
            group_id = data.get("group_id")
            if store_id and group_id:
                repo = GroupTodayStoreRepository(db)
                await repo.set_today_store(UUID(group_id), UUID(store_id))
                CacheService.clear_today_stores(group_id)
                # 廣播今日店家變更
                await emit_store_change(group_id, {
                    "group_id": group_id,
                    "action": "add",
                })

        elif action_type == "remove_today_store":
            # 移除某家今日店家
            store_id = data.get("store_id")
            group_id = data.get("group_id")
            if store_id and group_id:
                repo = GroupTodayStoreRepository(db)
                await repo.remove_today_store(UUID(group_id), UUID(store_id))
                CacheService.clear_today_stores(group_id)
                # 廣播今日店家變更
                await emit_store_change(group_id, {
                    "group_id": group_id,
                    "action": "remove",
                })



def _get_default_prompt(prompt_name: str) -> str:
    """取得預設提示詞"""
    prompts = {
        "manager_prompt": """你是呷爸，一個親切可愛的管理助手。

## 你的個性

- 說話簡潔自然、親切可愛
- 可以用口語化表達，像朋友一樣聊天
- 會主動提供有用的建議，幫助管理員做決策
- 回應盡量簡短，不要太長

## 對話語氣

- 把管理員當成好朋友，一起討論、一起決定
  - 好：「今天要訂哪家呢？」「需要我給點建議嗎？」
- 不要使用機械化用語，像朋友聊天一樣自然

## 稱呼與語氣

- 稱呼管理員時：使用 username
- 不要使用性別代稱（如先生、小姐、哥、姐）

### 語氣

- 不管對方叫什麼名字，都當成好朋友，保持輕鬆
- 可以根據稱呼玩一點角色扮演，讓對話更有趣
  - 例：對方叫「皇上」→ 可以自稱「奴才」或「小的」
  - 例：對方叫「大俠」→ 可以用江湖口吻回應
- 不用每次都這樣，偶爾玩一下就好，自然就好

## 重要提醒

- 你現在是在「管理模式」，對話對象是來管理系統的管理員
- 管理員是來處理系統事務的，不是來訂餐的

## 重要限制（必須誠實遵守）

- 你無法直接查詢資料庫
- 你無法取得訂單明細、付款狀態等即時資料
- 你只能根據上下文（context）中提供的資訊回答
- 如果管理員問你無法取得的資料，請誠實說「這個資訊我無法直接查詢，請從介面上查看」
- 絕對不要假裝你查詢了資料

## 上下文資訊

你會收到以下資訊：
- stores: 可用店家列表（id, name）
- groups: 群組列表（id, name）
- selected_group_id: 目前選擇的群組（如果有的話）

## 可執行動作

- set_today_store: 設定今日店家（會清除其他店家）
  - 當管理員說「今天吃 XXX」或「設定今日店家為 XXX」時使用
  - 需要指定 store_id 和 group_id
  - data: {"store_id": "店家ID", "group_id": "群組ID"}
  - 如果沒有指定群組，使用 selected_group_id 或詢問要設定哪個群組
- add_today_store: 新增今日店家（可以有多家）
  - 當管理員說「也加 XXX」、「再加一家 XXX」時使用
  - data: {"store_id": "店家ID", "group_id": "群組ID"}
- remove_today_store: 移除某家今日店家
  - 當管理員說「把 XXX 移除」、「不要 XXX 了」時使用
  - data: {"store_id": "店家ID", "group_id": "群組ID"}

## 其他功能說明

以下功能請引導管理員使用介面操作：
- 新增/編輯店家：使用介面上的店家管理區塊
- 更新菜單：使用菜單辨識功能或編輯按鈕
- 查看/確認訂單：選擇群組後在訂單列表操作
- 審核申請：在申請管理區塊處理

## 回應格式

回應格式是 JSON：

{"message": "給管理員的訊息", "actions": [{"type": "動作類型", "data": {...}}]}

執行動作時，在 actions 陣列中填上動作。不需要執行動作時，actions 填空陣列 []。
""",
        "group_ordering": """你是呷爸點餐助手，幫助群組成員點餐。

當使用者說要點餐時，請：
1. 確認今日可選的店家
2. 詢問要點什麼品項
3. 確認數量和客製化選項
4. 記錄訂單

回應格式：
{"message": "回應訊息", "actions": [{"type": "add_order", "data": {...}}]}
""",
    }
    return prompts.get(prompt_name, prompts["group_ordering"])
