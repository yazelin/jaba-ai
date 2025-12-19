"""管理員 API 路由"""
import secrets
from datetime import date, datetime, timedelta, timezone
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form, Header
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.store import Store
from app.models.group import Group, GroupApplication
from app.repositories import (
    UserRepository,
    GroupRepository,
    GroupApplicationRepository,
    GroupAdminRepository,
    StoreRepository,
    OrderSessionRepository,
    OrderRepository,
    AiPromptRepository,
    GroupTodayStoreRepository,
    SecurityLogRepository,
)
from app.services import MenuService, OrderService, CacheService

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ===== Session Token 管理 =====

# 簡單的 token 存儲（生產環境建議用 Redis）
_admin_sessions: dict[str, datetime] = {}
SESSION_EXPIRE_HOURS = 24


def _cleanup_expired_sessions():
    """清理過期 session"""
    now = datetime.now()
    expired = [k for k, v in _admin_sessions.items() if v < now]
    for k in expired:
        del _admin_sessions[k]


def create_admin_session() -> str:
    """建立 admin session，回傳 token"""
    _cleanup_expired_sessions()
    token = secrets.token_urlsafe(32)
    _admin_sessions[token] = datetime.now() + timedelta(hours=SESSION_EXPIRE_HOURS)
    return token


def verify_admin_token(authorization: str = Header(None)) -> bool:
    """驗證 admin token（用於 Depends）"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing authorization header")

    # 支援 "Bearer <token>" 格式
    token = authorization.replace("Bearer ", "") if authorization.startswith("Bearer ") else authorization

    if token not in _admin_sessions:
        raise HTTPException(status_code=401, detail="Invalid or expired token")

    if _admin_sessions[token] < datetime.now():
        del _admin_sessions[token]
        raise HTTPException(status_code=401, detail="Token expired")

    return True


# ===== Pydantic Models =====


class VerifyAdminRequest(BaseModel):
    username: str
    password: str


class StoreCreate(BaseModel):
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    note: Optional[str] = None
    scope: str = "global"  # global 或 group
    group_code: Optional[str] = None  # scope=group 時使用


class StoreUpdate(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    note: Optional[str] = None
    is_active: Optional[bool] = None


class StoreInfoUpdate(BaseModel):
    """店家資訊更新"""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None


class MenuSave(BaseModel):
    categories: List[dict]
    store_info: Optional[StoreInfoUpdate] = None


class MenuSaveDiff(BaseModel):
    """差異模式菜單儲存"""
    diff_mode: bool = True
    apply_items: List[dict] = []  # 要套用的品項（新增/修改）
    remove_items: List[str] = []  # 要移除的品項名稱
    store_info: Optional[StoreInfoUpdate] = None


class ApplicationReview(BaseModel):
    status: str  # approved or rejected
    note: Optional[str] = None


class SetTodayStore(BaseModel):
    store_ids: List[UUID]


class PromptUpdate(BaseModel):
    content: str


class ProxyOrderItem(BaseModel):
    name: str
    quantity: int = 1
    note: Optional[str] = None


class ProxyOrderCreate(BaseModel):
    user_id: UUID
    items: List[ProxyOrderItem]


class ProxyOrderUpdate(BaseModel):
    items: List[ProxyOrderItem]


# ===== Auth =====


@router.post("/verify")
async def verify_admin(
    request: VerifyAdminRequest,
    db: AsyncSession = Depends(get_db),
):
    """驗證超級管理員帳號密碼，成功回傳 token"""
    from app.repositories.system_repo import SuperAdminRepository

    repo = SuperAdminRepository(db)
    admin = await repo.verify_credentials(request.username, request.password)

    if admin:
        token = create_admin_session()
        return {"success": True, "token": token, "username": admin.username}

    raise HTTPException(status_code=401, detail="Invalid username or password")


# ===== Stores =====


@router.get("/stores")
async def get_all_stores(
    scope: Optional[str] = None,
    group_code: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得所有店家

    可選參數：
    - scope: 篩選店家層級 (global/group)
    - group_code: 篩選群組代碼 (scope=group 時使用)
    """
    repo = StoreRepository(db)

    if scope:
        stores = await repo.get_stores_by_scope(scope, group_code)
    else:
        stores = await repo.get_all_stores()

    return [
        {
            "id": str(store.id),
            "name": store.name,
            "phone": store.phone,
            "address": store.address,
            "description": store.description,
            "note": store.note,
            "is_active": store.is_active,
            "scope": store.scope,
            "group_code": store.group_code,
            "created_by_type": store.created_by_type,
        }
        for store in stores
    ]


@router.post("/stores")
async def create_store(
    data: StoreCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """建立店家（超級管理員）"""
    from app.broadcast import commit_and_notify, emit_store_change

    repo = StoreRepository(db)
    store_data = data.model_dump()
    store_data["created_by_type"] = "admin"  # 超管建立的店家
    store = Store(**store_data)
    store = await repo.create(store)

    # 廣播店家列表變更（全局廣播）
    await emit_store_change("all", {
        "action": "store_created",
        "store_id": str(store.id),
        "store_name": store.name,
        "scope": store.scope,
    })

    await commit_and_notify(db)

    return {
        "id": str(store.id),
        "name": store.name,
        "scope": store.scope,
        "group_code": store.group_code,
    }


@router.put("/stores/{store_id}")
async def update_store(
    store_id: UUID,
    data: StoreUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """更新店家"""
    from app.broadcast import commit_and_notify, emit_store_change

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(store, key, value)

    store = await repo.update(store)

    # 廣播店家列表變更（全局廣播）
    await emit_store_change("all", {
        "action": "store_updated",
        "store_id": str(store.id),
        "store_name": store.name,
        "scope": store.scope,
    })

    await commit_and_notify(db)

    return {"success": True}


@router.delete("/stores/{store_id}")
async def delete_store(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """刪除店家（硬刪除）"""
    from app.broadcast import commit_and_notify, emit_store_change

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    store_name = store.name
    store_scope = store.scope
    await db.delete(store)

    # 廣播店家列表變更（全局廣播）
    await emit_store_change("all", {
        "action": "store_deleted",
        "store_id": str(store_id),
        "store_name": store_name,
        "scope": store_scope,
    })

    await commit_and_notify(db)
    CacheService.clear_menu(str(store_id))

    return {"success": True}


# ===== Menu =====


@router.post("/menu/recognize")
async def recognize_menu_only(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """辨識菜單圖片（不需要指定店家）"""
    service = MenuService(db)
    image_bytes = await file.read()
    result = await service.recognize_menu_image(image_bytes)
    return result


@router.post("/stores/{store_id}/menu/recognize")
async def recognize_menu(
    store_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """辨識菜單圖片並與現有菜單比對"""
    service = MenuService(db)
    image_bytes = await file.read()

    # 辨識新菜單
    recognized_menu = await service.recognize_menu_image(image_bytes)

    # 取得現有菜單
    existing_menu = await service.get_store_menu(store_id)

    # 比對差異
    diff = None
    if existing_menu:
        diff = service.compare_menus(existing_menu, recognized_menu)

    return {
        "recognized_menu": recognized_menu,
        "existing_menu": existing_menu,
        "diff": diff,
        "store_id": str(store_id),
    }


@router.post("/stores/{store_id}/menu")
async def save_menu(
    store_id: UUID,
    data: MenuSave,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """儲存菜單（完整覆蓋）"""
    from app.broadcast import emit_store_change

    # 更新店家資訊（如果有提供）
    store_info_updated = False
    if data.store_info:
        repo = StoreRepository(db)
        store = await repo.get_by_id(store_id)
        if store:
            if data.store_info.name:
                store.name = data.store_info.name
            if data.store_info.phone is not None:
                store.phone = data.store_info.phone
            if data.store_info.address is not None:
                store.address = data.store_info.address
            if data.store_info.description is not None:
                store.description = data.store_info.description
            await repo.update(store)
            store_info_updated = True

    service = MenuService(db)
    menu = await service.save_menu(store_id, data.categories)

    # 提交變更
    await db.commit()

    # 廣播店家資訊變更（全局廣播，因為超管的店家是 global scope）
    if store_info_updated:
        await emit_store_change("all", {
            "action": "store_updated",
            "store_id": str(store_id),
            "store_name": store.name,
            "scope": store.scope,
        })

    return {"success": True, "menu_id": str(menu.id)}


@router.post("/stores/{store_id}/menu/save")
async def save_menu_diff(
    store_id: UUID,
    data: MenuSaveDiff,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """儲存菜單（支援差異模式）

    diff_mode=true: 選擇性更新（套用指定品項、移除指定品項）
    diff_mode=false: 完整覆蓋（需提供完整分類結構）
    """
    from app.broadcast import emit_store_change

    # 更新店家資訊（如果有提供）
    store_info_updated = False
    store = None
    if data.store_info:
        repo = StoreRepository(db)
        store = await repo.get_by_id(store_id)
        if store:
            if data.store_info.name:
                store.name = data.store_info.name
            if data.store_info.phone is not None:
                store.phone = data.store_info.phone
            if data.store_info.address is not None:
                store.address = data.store_info.address
            if data.store_info.description is not None:
                store.description = data.store_info.description
            await repo.update(store)
            store_info_updated = True

    service = MenuService(db)

    if not data.diff_mode:
        # 完整覆蓋模式（需要從 apply_items 重建分類結構）
        categories_data = service._group_items_by_category(data.apply_items)
        menu = await service.save_menu(store_id, categories_data)
    else:
        # 差異模式
        menu = await service.save_menu_diff(
            store_id,
            apply_items=data.apply_items,
            remove_items=data.remove_items,
        )

    # 提交變更
    await db.commit()

    # 廣播店家資訊變更（全局廣播，因為超管的店家是 global scope）
    if store_info_updated and store:
        await emit_store_change("all", {
            "action": "store_updated",
            "store_id": str(store_id),
            "store_name": store.name,
            "scope": store.scope,
        })

    return {"success": True, "menu_id": str(menu.id)}


@router.delete("/stores/{store_id}/menu")
async def delete_menu(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """刪除店家的菜單"""
    service = MenuService(db)
    await service.delete_menu(store_id)
    return {"success": True}


@router.get("/stores/{store_id}/menu/compare")
async def compare_menu(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得現有菜單（用於比較）"""
    service = MenuService(db)
    menu = await service.get_store_menu(store_id)
    return menu or {"categories": []}


# ===== Groups =====


@router.get("/groups")
async def get_all_groups(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得所有已啟用的群組（用於訂單管理下拉選單）"""
    repo = GroupRepository(db)
    groups = await repo.get_active_groups()
    return [
        {
            "id": str(group.id),
            "line_group_id": group.line_group_id,
            "name": group.name,
            "status": group.status,
            "activated_at": group.activated_at.isoformat() if group.activated_at else None,
        }
        for group in groups
    ]


@router.get("/groups/list")
async def get_groups_paginated(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得群組列表（分頁）

    Args:
        limit: 每頁數量（預設 20）
        offset: 偏移量
        search: 搜尋關鍵字（名稱或代碼）
        status: 狀態篩選（all/active/suspended/pending）
    """
    from app.models import GroupApplication
    from sqlalchemy import select

    repo = GroupRepository(db)
    groups, total = await repo.get_all_paginated(
        limit=limit, offset=offset, search=search, status=status
    )

    # 取得每個群組的統計資訊和申請名稱
    group_list = []
    for group in groups:
        stats = await repo.get_group_with_stats(group.id)

        # 取得最新核准的申請名稱
        app_result = await db.execute(
            select(GroupApplication)
            .where(GroupApplication.line_group_id == group.line_group_id)
            .where(GroupApplication.status == "approved")
            .order_by(GroupApplication.reviewed_at.desc())
            .limit(1)
        )
        latest_app = app_result.scalar_one_or_none()

        group_list.append({
            "id": str(group.id),
            "line_group_id": group.line_group_id,
            "name": group.name,  # LINE 群組名稱
            "application_name": latest_app.group_name if latest_app else None,  # 申請的群組名稱
            "group_code": group.group_code,
            "status": group.status,
            "description": group.description,
            "created_at": group.created_at.isoformat() if group.created_at else None,
            "activated_at": group.activated_at.isoformat() if group.activated_at else None,
            "member_count": stats["member_count"] if stats else 0,
            "admin_count": stats["admin_count"] if stats else 0,
        })

    return {
        "groups": group_list,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/groups/{group_id}")
async def get_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得群組詳情"""
    repo = GroupRepository(db)
    admin_repo = GroupAdminRepository(db)

    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    admins = await admin_repo.get_group_admins(group_id)

    return {
        "id": str(group.id),
        "line_group_id": group.line_group_id,
        "name": group.name,
        "description": group.description,
        "status": group.status,
        "activated_at": group.activated_at.isoformat() if group.activated_at else None,
        "admins": [
            {
                "user_id": str(admin.user_id),
                "display_name": admin.user.display_name if admin.user else None,
            }
            for admin in admins
        ],
    }


# ===== Group Admins =====


@router.post("/groups/{group_id}/admins")
async def add_group_admin(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """新增群組管理員"""
    admin_repo = GroupAdminRepository(db)

    admin = await admin_repo.add_admin(group_id, user_id)
    return {"success": True}


@router.delete("/groups/{group_id}/admins/{user_id}")
async def remove_group_admin(
    group_id: UUID,
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """移除群組管理員"""
    admin_repo = GroupAdminRepository(db)

    # 檢查是否為最後一個管理員
    admins = await admin_repo.get_group_admins(group_id)
    if len(admins) <= 1:
        raise HTTPException(
            status_code=400,
            detail="無法移除唯一的管理員",
        )

    # 移除管理員
    removed = await admin_repo.remove_admin(group_id, user_id)
    if not removed:
        raise HTTPException(status_code=404, detail="找不到該管理員")

    return {"success": True}


# ===== Applications =====


@router.get("/applications")
async def get_applications(
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得群組申請列表"""
    repo = GroupApplicationRepository(db)
    if status == "pending":
        applications = await repo.get_pending_applications()
    else:
        applications = await repo.get_all_applications()

    return [
        {
            "id": str(app.id),
            "line_group_id": app.line_group_id,
            "group_name": app.group_name,
            "contact_info": app.contact_info,
            "group_code": app.group_code,
            "status": app.status,
            "created_at": app.created_at.isoformat(),
            "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None,
            "review_note": app.review_note,
        }
        for app in applications
    ]


@router.post("/applications/{app_id}/review")
async def review_application(
    app_id: UUID,
    data: ApplicationReview,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """審核群組申請"""
    from app.models.user import User
    from app.models.group import GroupAdmin

    app_repo = GroupApplicationRepository(db)
    group_repo = GroupRepository(db)
    user_repo = UserRepository(db)
    admin_repo = GroupAdminRepository(db)

    application = await app_repo.get_by_id(app_id)
    if not application:
        raise HTTPException(status_code=404, detail="Application not found")

    application.status = data.status
    application.reviewed_at = datetime.now(timezone.utc)
    application.review_note = data.note
    await app_repo.update(application)

    # 如果通過，建立或啟用群組
    # 注意：管理員由真人在群組中輸入「管理員 [代碼]」綁定，不在此建立虛擬用戶
    if data.status == "approved":
        group = await group_repo.get_by_line_group_id(application.line_group_id)
        if not group:
            group = Group(
                line_group_id=application.line_group_id,
                name=application.group_name,
                group_code=application.group_code,
                status="active",
                activated_at=datetime.now(timezone.utc),
            )
            await group_repo.create(group)
        else:
            group.status = "active"
            group.name = application.group_name  # 更新為申請的群組名稱
            group.group_code = application.group_code
            group.activated_at = datetime.now(timezone.utc)
            await group_repo.update(group)

    await db.commit()
    return {"success": True}


# ===== Today Stores =====


@router.get("/groups/{group_id}/today-stores")
async def get_group_today_stores(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得群組今日店家"""
    repo = GroupTodayStoreRepository(db)
    today_stores = await repo.get_today_stores(group_id)

    return [
        {
            "store_id": str(ts.store_id),
            "store_name": ts.store.name if ts.store else None,
        }
        for ts in today_stores
    ]


@router.post("/groups/{group_id}/today-stores")
async def set_today_stores(
    group_id: UUID,
    data: SetTodayStore,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """設定群組今日店家"""
    from app.broadcast import commit_and_notify, emit_store_change

    repo = GroupTodayStoreRepository(db)
    store_repo = StoreRepository(db)

    # 清除現有今日店家
    await repo.clear_today_stores(group_id)

    # 設定新的今日店家
    stores_info = []
    for store_id in data.store_ids:
        await repo.set_today_store(group_id, store_id)
        store = await store_repo.get_by_id(store_id)
        if store:
            stores_info.append({
                "store_id": str(store_id),
                "store_name": store.name,
            })

    # 廣播今日店家變更
    await emit_store_change(str(group_id), {
        "group_id": str(group_id),
        "stores": stores_info,
    })

    # 提交並發送通知
    await commit_and_notify(db)

    # 清除快取
    CacheService.clear_today_stores(str(group_id))

    return {"success": True}


# ===== Orders =====


@router.get("/groups/{group_id}/orders")
async def get_group_orders(
    group_id: UUID,
    all_sessions: bool = False,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得群組訂單

    預設只返回最新的 session（active 或今日最近結束的）
    若 all_sessions=True 則返回今日所有 sessions
    """
    session_repo = OrderSessionRepository(db)

    # 先檢查是否有 active session
    active_session = await session_repo.get_active_session(group_id)

    if active_session:
        # 有進行中的 session，只返回這個
        sessions = [active_session]
    else:
        # 沒有進行中的，取今日的 sessions
        today = date.today()
        sessions = await session_repo.get_group_sessions(group_id, today, today)
        if not all_sessions and sessions:
            # 只取最新的一個（按 started_at 降序，取第一個）
            sessions = [sessions[0]]

    result = []
    for session in sessions:
        session_data = await session_repo.get_with_orders(session.id)
        if session_data:
            result.append({
                "session_id": str(session.id),
                "status": session.status,
                "started_at": session.started_at.isoformat(),
                "ended_at": session.ended_at.isoformat() if session.ended_at else None,
                "orders": [
                    {
                        "id": str(order.id),
                        "user_id": str(order.user_id),
                        "display_name": order.user.display_name if order.user else "未知",
                        "total": float(order.total_amount),
                        "payment_status": order.payment_status,
                        "items": [
                            {
                                "name": item.name,
                                "quantity": item.quantity,
                                "subtotal": float(item.subtotal),
                                "note": item.note,
                                "options": item.options,
                            }
                            for item in order.items
                        ],
                    }
                    for order in session_data.orders
                ],
            })

    return result


@router.post("/orders/{order_id}/mark-paid")
async def mark_order_paid(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """標記訂單已付款"""
    from app.broadcast import commit_and_notify

    service = OrderService(db)
    await service.mark_paid(order_id)
    await commit_and_notify(db)
    return {"success": True}


@router.post("/orders/{order_id}/refund")
async def refund_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """退款"""
    from app.broadcast import commit_and_notify

    service = OrderService(db)
    await service.refund(order_id)
    await commit_and_notify(db)
    return {"success": True}


@router.delete("/orders/{order_id}")
async def delete_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """刪除訂單"""
    service = OrderService(db)
    await service.cancel_order(order_id)
    return {"success": True}


@router.delete("/sessions/{session_id}/orders")
async def clear_session_orders(
    session_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """清除 Session 所有訂單"""
    session_repo = OrderSessionRepository(db)

    # 驗證 Session 存在
    session = await session_repo.get_by_id(session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    from app.broadcast import commit_and_notify

    service = OrderService(db)
    deleted_count = await service.clear_session_orders(session_id)
    await commit_and_notify(db)
    return {"success": True, "deleted_count": deleted_count}


# ===== Proxy Orders (代理點餐) =====


@router.post("/groups/{group_id}/proxy-orders")
async def create_proxy_order(
    group_id: UUID,
    data: ProxyOrderCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """代理建立訂單（超級管理員用）"""
    from decimal import Decimal
    from app.broadcast import commit_and_notify, emit_order_update
    from app.models.order import Order, OrderItem
    from app.repositories import MenuItemRepository
    from sqlalchemy.orm import selectinload
    from sqlalchemy import select
    from app.models.menu import Menu, MenuCategory, MenuItem

    session_repo = OrderSessionRepository(db)
    order_repo = OrderRepository(db)
    user_repo = UserRepository(db)
    today_store_repo = GroupTodayStoreRepository(db)

    # 驗證群組有進行中的 Session
    active_session = await session_repo.get_active_session(group_id)
    if not active_session:
        raise HTTPException(status_code=400, detail="群組沒有進行中的點餐")

    # 驗證使用者存在
    user = await user_repo.get_by_id(data.user_id)
    if not user:
        raise HTTPException(status_code=404, detail="找不到該使用者")

    # 取得今日店家
    today_stores = await today_store_repo.get_today_stores(group_id)
    if not today_stores:
        raise HTTPException(status_code=400, detail="今日尚未設定店家")

    store_id = today_stores[0].store_id

    # 取得或建立使用者訂單
    order = await order_repo.get_by_session_and_user(active_session.id, data.user_id)
    if not order:
        order = Order(
            session_id=active_session.id,
            user_id=data.user_id,
            store_id=store_id,
        )
        db.add(order)
        await db.flush()
        await db.refresh(order)

    # 從菜單找價格並新增品項
    for item_data in data.items:
        # 從菜單找價格
        result = await db.execute(
            select(MenuItem)
            .join(MenuCategory)
            .join(Menu)
            .where(Menu.store_id == store_id)
        )
        menu_items = result.scalars().all()

        price = 0
        for mi in menu_items:
            if mi.name == item_data.name or item_data.name in mi.name:
                price = float(mi.price)
                break

        if price == 0:
            raise HTTPException(
                status_code=400,
                detail=f"菜單中找不到「{item_data.name}」"
            )

        order_item = OrderItem(
            order_id=order.id,
            name=item_data.name,
            quantity=item_data.quantity,
            unit_price=Decimal(str(price)),
            subtotal=Decimal(str(price * item_data.quantity)),
            note=item_data.note or "",
        )
        db.add(order_item)

    await db.flush()

    # 重新計算總金額
    order = await order_repo.calculate_total(order)

    # 廣播訂單更新
    await emit_order_update(str(group_id), {
        "group_id": str(group_id),
        "action": "created",
        "user_id": str(user.id),
        "display_name": user.display_name,
        "proxy": True,
    })

    await commit_and_notify(db)

    return {"success": True, "order_id": str(order.id)}


@router.put("/groups/{group_id}/proxy-orders/{order_id}")
async def update_proxy_order(
    group_id: UUID,
    order_id: UUID,
    data: ProxyOrderUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """代理修改訂單（超級管理員用）"""
    from decimal import Decimal
    from app.broadcast import commit_and_notify, emit_order_update
    from app.models.order import OrderItem
    from app.repositories import OrderItemRepository
    from sqlalchemy import select
    from app.models.menu import Menu, MenuCategory, MenuItem

    order_repo = OrderRepository(db)
    order_item_repo = OrderItemRepository(db)
    today_store_repo = GroupTodayStoreRepository(db)
    user_repo = UserRepository(db)

    # 驗證訂單存在
    order = await order_repo.get_by_id(order_id)
    if not order:
        raise HTTPException(status_code=404, detail="找不到該訂單")

    # 取得今日店家
    today_stores = await today_store_repo.get_today_stores(group_id)
    if not today_stores:
        raise HTTPException(status_code=400, detail="今日尚未設定店家")

    store_id = today_stores[0].store_id

    # 刪除現有品項
    for item in order.items:
        await order_item_repo.delete(item)

    # 從菜單找價格並新增品項
    for item_data in data.items:
        result = await db.execute(
            select(MenuItem)
            .join(MenuCategory)
            .join(Menu)
            .where(Menu.store_id == store_id)
        )
        menu_items = result.scalars().all()

        price = 0
        for mi in menu_items:
            if mi.name == item_data.name or item_data.name in mi.name:
                price = float(mi.price)
                break

        if price == 0:
            raise HTTPException(
                status_code=400,
                detail=f"菜單中找不到「{item_data.name}」"
            )

        order_item = OrderItem(
            order_id=order.id,
            name=item_data.name,
            quantity=item_data.quantity,
            unit_price=Decimal(str(price)),
            subtotal=Decimal(str(price * item_data.quantity)),
            note=item_data.note or "",
        )
        db.add(order_item)

    await db.flush()

    # 重新計算總金額
    order = await order_repo.calculate_total(order)

    # 取得使用者資訊
    user = await user_repo.get_by_id(order.user_id)

    # 廣播訂單更新
    await emit_order_update(str(group_id), {
        "group_id": str(group_id),
        "action": "updated",
        "user_id": str(order.user_id),
        "display_name": user.display_name if user else "未知",
        "proxy": True,
    })

    await commit_and_notify(db)

    return {"success": True}


# ===== AI Prompts =====


@router.get("/prompts")
async def get_prompts(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得所有 AI 提示詞"""
    repo = AiPromptRepository(db)
    prompts = await repo.get_all_prompts()
    return [
        {
            "id": str(p.id),
            "name": p.name,
            "content": p.content,
            "updated_at": p.updated_at.isoformat(),
        }
        for p in prompts
    ]


@router.put("/prompts/{name}")
async def update_prompt(
    name: str,
    data: PromptUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """更新 AI 提示詞"""
    repo = AiPromptRepository(db)
    await repo.set_prompt(name, data.content)
    CacheService.clear_prompt(name)
    return {"success": True}


# ===== Maintenance =====


@router.get("/maintenance/chat-stats")
async def get_chat_stats(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得對話統計資訊"""
    from app.repositories.chat_repo import ChatRepository

    repo = ChatRepository(db)
    stats = await repo.get_stats()
    return stats


@router.post("/maintenance/cleanup-chat")
async def cleanup_chat_messages(
    retention_days: int = 365,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """清理舊對話記錄（預設保留一年）"""
    from app.repositories.chat_repo import ChatRepository

    if retention_days < 30:
        raise HTTPException(status_code=400, detail="Retention days must be at least 30")

    repo = ChatRepository(db)
    deleted_count = await repo.cleanup_old_messages(retention_days)
    return {
        "success": True,
        "deleted_count": deleted_count,
        "retention_days": retention_days,
    }


# ===== 安全日誌 =====


@router.get("/security-logs")
async def get_security_logs(
    limit: int = 50,
    offset: int = 0,
    line_user_id: Optional[str] = None,
    line_group_id: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得安全日誌列表"""
    repo = SecurityLogRepository(db)

    logs = await repo.get_recent(
        limit=min(limit, 100),  # 最多 100 筆
        offset=offset,
        line_user_id=line_user_id,
        line_group_id=line_group_id,
    )

    total = await repo.get_total_count(
        line_user_id=line_user_id,
        line_group_id=line_group_id,
    )

    return {
        "logs": [
            {
                "id": str(log.id),
                "line_user_id": log.line_user_id,
                "display_name": log.display_name,
                "line_group_id": log.line_group_id,
                "original_message": log.original_message,
                "sanitized_message": log.sanitized_message,
                "trigger_reasons": log.trigger_reasons,
                "context_type": log.context_type,
                "created_at": log.created_at.isoformat() if log.created_at else None,
            }
            for log in logs
        ],
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/security-logs/stats")
async def get_security_logs_stats(
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得安全日誌統計"""
    repo = SecurityLogRepository(db)
    stats = await repo.get_stats()
    return stats


# ===== User Management =====


@router.get("/users")
async def get_users(
    limit: int = 20,
    offset: int = 0,
    search: Optional[str] = None,
    status: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得使用者列表（分頁）

    Args:
        limit: 每頁數量（預設 20）
        offset: 偏移量
        search: 搜尋關鍵字（名稱或 LINE ID）
        status: 狀態篩選（all/active/banned）
    """
    repo = UserRepository(db)
    users, total = await repo.get_all_paginated(
        limit=limit, offset=offset, search=search, status=status
    )

    # 取得每個使用者的統計資訊
    user_list = []
    for user in users:
        stats = await repo.get_user_with_stats(user.id)
        user_list.append({
            "id": str(user.id),
            "line_user_id": user.line_user_id,
            "display_name": user.display_name,
            "picture_url": user.picture_url,
            "is_banned": user.is_banned,
            "banned_at": user.banned_at.isoformat() if user.banned_at else None,
            "created_at": user.created_at.isoformat() if user.created_at else None,
            "group_count": stats["group_count"] if stats else 0,
            "order_count": stats["order_count"] if stats else 0,
        })

    return {
        "users": user_list,
        "total": total,
        "limit": limit,
        "offset": offset,
    }


@router.get("/users/{user_id}")
async def get_user_detail(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得使用者詳情"""
    repo = UserRepository(db)
    stats = await repo.get_user_with_stats(user_id)

    if not stats:
        raise HTTPException(status_code=404, detail="使用者不存在")

    user = stats["user"]
    groups = await repo.get_user_groups(user_id)
    orders = await repo.get_user_recent_orders(user_id)

    # 取得違規記錄
    security_repo = SecurityLogRepository(db)
    violations = await security_repo.get_recent(
        limit=10, line_user_id=user.line_user_id
    )

    return {
        "id": str(user.id),
        "line_user_id": user.line_user_id,
        "display_name": user.display_name,
        "picture_url": user.picture_url,
        "preferences": user.preferences,
        "is_banned": user.is_banned,
        "banned_at": user.banned_at.isoformat() if user.banned_at else None,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "group_count": stats["group_count"],
        "order_count": stats["order_count"],
        "groups": groups,
        "recent_orders": orders,
        "violations": [
            {
                "id": str(v.id),
                "original_message": v.original_message[:100] + "..." if len(v.original_message) > 100 else v.original_message,
                "trigger_reasons": v.trigger_reasons,
                "created_at": v.created_at.isoformat(),
            }
            for v in violations
        ],
    }


@router.post("/users/{user_id}/ban")
async def ban_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """封鎖使用者"""
    repo = UserRepository(db)
    user = await repo.ban_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")

    await db.commit()

    return {
        "success": True,
        "message": f"已封鎖使用者 {user.display_name}",
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "is_banned": user.is_banned,
            "banned_at": user.banned_at.isoformat() if user.banned_at else None,
        },
    }


@router.post("/users/{user_id}/unban")
async def unban_user(
    user_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """解除封鎖使用者"""
    repo = UserRepository(db)
    user = await repo.unban_user(user_id)

    if not user:
        raise HTTPException(status_code=404, detail="使用者不存在")

    await db.commit()

    return {
        "success": True,
        "message": f"已解除封鎖使用者 {user.display_name}",
        "user": {
            "id": str(user.id),
            "display_name": user.display_name,
            "is_banned": user.is_banned,
        },
    }


# ===== Group Management (Enhanced) =====


class UpdateGroupInfo(BaseModel):
    """更新群組資訊"""
    name: Optional[str] = None
    description: Optional[str] = None
    group_code: Optional[str] = None


@router.get("/groups/{group_id}/detail")
async def get_group_detail(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得群組詳情"""
    from app.repositories.group_repo import GroupMemberRepository, GroupAdminRepository

    repo = GroupRepository(db)
    stats = await repo.get_group_with_stats(group_id)

    if not stats:
        raise HTTPException(status_code=404, detail="群組不存在")

    group = stats["group"]

    # 取得成員列表
    member_repo = GroupMemberRepository(db)
    members = await member_repo.get_group_members(group_id)

    # 取得管理員列表
    admin_repo = GroupAdminRepository(db)
    admins = await admin_repo.get_group_admins(group_id)
    admin_user_ids = {a.user_id for a in admins}

    return {
        "id": str(group.id),
        "line_group_id": group.line_group_id,
        "name": group.name,
        "group_code": group.group_code,
        "status": group.status,
        "description": group.description,
        "created_at": group.created_at.isoformat() if group.created_at else None,
        "activated_at": group.activated_at.isoformat() if group.activated_at else None,
        "member_count": stats["member_count"],
        "admin_count": stats["admin_count"],
        "members": [
            {
                "id": str(m.user_id),
                "display_name": m.user.display_name if m.user else None,
                "picture_url": m.user.picture_url if m.user else None,
                "is_admin": m.user_id in admin_user_ids,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
            for m in members
        ],
    }


@router.put("/groups/{group_id}")
async def update_group(
    group_id: UUID,
    data: UpdateGroupInfo,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """更新群組資訊"""
    repo = GroupRepository(db)
    group = await repo.update_group_info(
        group_id,
        name=data.name,
        description=data.description,
        group_code=data.group_code,
    )

    if not group:
        raise HTTPException(status_code=404, detail="群組不存在")

    await db.commit()

    return {
        "success": True,
        "message": "群組資訊已更新",
        "group": {
            "id": str(group.id),
            "name": group.name,
            "group_code": group.group_code,
            "description": group.description,
        },
    }


@router.post("/groups/{group_id}/suspend")
async def suspend_group(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """停用群組"""
    repo = GroupRepository(db)
    group = await repo.suspend_group(group_id)

    if not group:
        raise HTTPException(status_code=404, detail="群組不存在")

    await db.commit()

    return {
        "success": True,
        "message": f"已停用群組 {group.name}",
        "group": {
            "id": str(group.id),
            "name": group.name,
            "status": group.status,
        },
    }


@router.post("/groups/{group_id}/activate")
async def activate_group_endpoint(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """啟用群組"""
    repo = GroupRepository(db)
    group = await repo.activate_group(group_id)

    if not group:
        raise HTTPException(status_code=404, detail="群組不存在")

    await db.commit()

    return {
        "success": True,
        "message": f"已啟用群組 {group.name}",
        "group": {
            "id": str(group.id),
            "name": group.name,
            "status": group.status,
        },
    }


@router.delete("/groups/{group_id}")
async def delete_group_endpoint(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """刪除群組（硬刪除）"""
    repo = GroupRepository(db)

    # 先取得群組資訊（用於回傳訊息）
    group = await repo.get_by_id(group_id)
    if not group:
        raise HTTPException(status_code=404, detail="群組不存在")

    group_name = group.name
    group_id_str = str(group.id)

    # 執行刪除
    await repo.delete_group(group_id)
    await db.commit()

    return {
        "success": True,
        "message": f"已刪除群組 {group_name}",
        "group": {
            "id": group_id_str,
            "name": group_name,
        },
    }


@router.get("/groups/{group_id}/members")
async def get_group_members(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_admin_token),
):
    """取得群組成員列表"""
    from app.repositories.group_repo import GroupMemberRepository, GroupAdminRepository

    repo = GroupRepository(db)
    group = await repo.get_by_id(group_id)

    if not group:
        raise HTTPException(status_code=404, detail="群組不存在")

    # 取得成員列表
    member_repo = GroupMemberRepository(db)
    members = await member_repo.get_group_members(group_id)

    # 取得管理員列表
    admin_repo = GroupAdminRepository(db)
    admins = await admin_repo.get_group_admins(group_id)
    admin_user_ids = {a.user_id for a in admins}

    return {
        "group_id": str(group_id),
        "group_name": group.name,
        "members": [
            {
                "id": str(m.user_id),
                "display_name": m.user.display_name if m.user else None,
                "picture_url": m.user.picture_url if m.user else None,
                "line_user_id": m.user.line_user_id if m.user else None,
                "is_admin": m.user_id in admin_user_ids,
                "is_banned": m.user.is_banned if m.user else False,
                "joined_at": m.joined_at.isoformat() if m.joined_at else None,
            }
            for m in members
        ],
        "total": len(members),
    }
