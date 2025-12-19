"""AI 聊天 API 路由（超管後台專用）"""
import logging
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
from app.repositories.system_repo import AiLogRepository
from app.models.system import AiLog
from app.broadcast import commit_and_notify, emit_store_change
from app.routers.admin import verify_admin_token

logger = logging.getLogger("jaba.chat")

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
    _: bool = Depends(verify_admin_token),
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
            raise ValueError(f"找不到提示詞：{prompt_name}，請確認資料庫已執行 alembic upgrade")

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

    # 記錄 AI Log（超管對話，user_id 和 group_id 為空）
    await _record_ai_log(db, result)

    # 執行動作（如果有的話）
    if result.get("actions"):
        await _execute_actions(db, result["actions"])

    await commit_and_notify(db)

    return ChatResponse(
        message=result.get("message", ""),
        actions=result.get("actions", []),
    )


async def _record_ai_log(db: AsyncSession, ai_response: dict) -> None:
    """記錄 AI 對話日誌"""
    try:
        ai_log = AiLog(
            user_id=None,  # 超管對話，無關聯使用者
            group_id=None,  # 超管對話，無關聯群組
            model=ai_response.get("_model", "unknown"),
            input_prompt=ai_response.get("_input_prompt", ""),
            raw_response=ai_response.get("_raw", ""),
            parsed_message=ai_response.get("message"),
            parsed_actions=ai_response.get("actions"),
            success=True,
            duration_ms=ai_response.get("_duration_ms"),
            input_tokens=ai_response.get("_input_tokens"),
            output_tokens=ai_response.get("_output_tokens"),
        )
        ai_log_repo = AiLogRepository(db)
        await ai_log_repo.create(ai_log)
    except Exception as e:
        logger.warning(f"Failed to record AI log: {e}")


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

