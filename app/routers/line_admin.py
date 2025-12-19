"""LINE 管理員 API 路由"""
from datetime import date, datetime
from typing import Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.repositories import (
    UserRepository,
    GroupRepository,
    GroupAdminRepository,
    GroupApplicationRepository,
    OrderSessionRepository,
    GroupTodayStoreRepository,
    StoreRepository,
)

router = APIRouter(prefix="/api/line-admin", tags=["line-admin"])


# ===== Helper Functions =====


async def get_group_by_code(db: AsyncSession, group_code: str):
    """根據 group_code 取得 Group"""
    group_repo = GroupRepository(db)
    return await group_repo.get_by_code(group_code)


# ===== Pydantic Models =====


class LineAdminLogin(BaseModel):
    password: str  # 群組代碼（API 欄位名保持相容）


class ChangeGroupCode(BaseModel):
    current_code: str
    new_code: str


class GroupApplicationCreate(BaseModel):
    line_group_id: str
    group_name: str
    contact_info: str  # 合併後的聯絡資訊欄位
    group_code: str  # 群組代碼（取代原 password）


class SetTodayStore(BaseModel):
    store_ids: list[UUID]


class StoreCreate(BaseModel):
    """LINE 管建立店家"""
    name: str
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    note: Optional[str] = None


class StoreUpdate(BaseModel):
    """LINE 管更新店家"""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None
    note: Optional[str] = None
    is_active: Optional[bool] = None


class StoreInfoUpdate(BaseModel):
    """店家資訊更新（從菜單辨識）"""
    name: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    description: Optional[str] = None


class MenuSave(BaseModel):
    """菜單儲存（完整覆蓋）"""
    categories: list[dict]
    store_info: Optional[StoreInfoUpdate] = None  # 可選的店家資訊更新


class MenuSaveDiff(BaseModel):
    """菜單儲存（差異模式）"""
    diff_mode: bool = True
    apply_items: list[dict] = []
    remove_items: list[str] = []
    store_info: Optional[StoreInfoUpdate] = None  # 可選的店家資訊更新


# ===== Auth =====


@router.post("/login")
async def line_admin_login(
    data: LineAdminLogin,
    db: AsyncSession = Depends(get_db),
):
    """LINE 管理員登入（使用群組代碼）"""
    app_repo = GroupApplicationRepository(db)
    group_repo = GroupRepository(db)

    # 用代碼查找已核准的申請
    applications = await app_repo.get_approved_by_password(data.password)

    if not applications:
        raise HTTPException(status_code=401, detail="代碼錯誤")

    # 取得對應的群組（以 group_id 去重，避免同群組有多筆申請時重複）
    groups = []
    seen_group_ids = set()
    for app in applications:
        group = await group_repo.get_by_line_group_id(app.line_group_id)
        if group and group.status == "active" and str(group.id) not in seen_group_ids:
            seen_group_ids.add(str(group.id))
            groups.append({
                "group_id": str(group.id),
                "group_name": group.name or app.group_name,
            })

    if not groups:
        raise HTTPException(status_code=401, detail="沒有可管理的群組")

    return {
        "success": True,
        "groups": groups,
    }


# ===== Applications =====


@router.post("/applications")
async def create_application(
    data: GroupApplicationCreate,
    db: AsyncSession = Depends(get_db),
):
    """提交群組申請"""
    from app.models.group import GroupApplication

    repo = GroupApplicationRepository(db)

    # 檢查是否已有待審核的申請
    existing = await repo.get_pending_by_line_group_id(data.line_group_id)
    if existing:
        raise HTTPException(
            status_code=400,
            detail="已有待審核的申請，請等待審核結果",
        )

    # 驗證群組代碼長度
    if len(data.group_code) < 4 or len(data.group_code) > 20:
        raise HTTPException(
            status_code=400,
            detail="群組代碼長度需為 4-20 字元",
        )

    application = GroupApplication(
        line_group_id=data.line_group_id,
        group_name=data.group_name,
        contact_info=data.contact_info,
        group_code=data.group_code,
    )
    application = await repo.create(application)

    return {
        "success": True,
        "application_id": str(application.id),
    }


@router.get("/applications/{line_group_id}")
async def get_application_status(
    line_group_id: str,
    db: AsyncSession = Depends(get_db),
):
    """查詢申請狀態（以 LINE 群組 ID）"""
    repo = GroupApplicationRepository(db)
    applications = await repo.get_by_line_group_id(line_group_id)
    return _format_applications(applications)


@router.get("/applications/by-code/{group_code}")
async def get_application_status_by_code(
    group_code: str,
    db: AsyncSession = Depends(get_db),
):
    """查詢申請狀態（以群組代碼）"""
    repo = GroupApplicationRepository(db)
    applications = await repo.get_by_group_code(group_code)
    return _format_applications(applications)


def _format_applications(applications):
    """格式化申請列表回應"""
    def mask_code(code: str) -> str:
        """遮蔽代碼，只顯示前後各一字元"""
        if not code:
            return ""
        if len(code) <= 2:
            return code[0] + "*"
        return code[0] + "*" * (len(code) - 2) + code[-1]

    return [
        {
            "id": str(app.id),
            "status": app.status,
            "group_name": app.group_name,
            "created_at": app.created_at.isoformat(),
            "reviewed_at": app.reviewed_at.isoformat() if app.reviewed_at else None,
            "review_note": app.review_note,
            "code_hint": mask_code(app.group_code) if app.group_code else None,
        }
        for app in applications
    ]


# ===== Group Management =====


@router.get("/groups/{group_id}")
async def get_group_info(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得群組資訊"""
    repo = GroupRepository(db)
    group = await repo.get_by_id(group_id)

    if not group:
        raise HTTPException(status_code=404, detail="Group not found")

    return {
        "id": str(group.id),
        "name": group.name,
        "status": group.status,
        "activated_at": group.activated_at.isoformat() if group.activated_at else None,
    }


@router.get("/groups/{group_id}/orders")
async def get_group_orders(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得群組訂單（只返回最新 session）"""
    session_repo = OrderSessionRepository(db)

    # 先檢查是否有 active session
    active_session = await session_repo.get_active_session(group_id)

    if active_session:
        sessions = [active_session]
    else:
        # 沒有進行中的，取今日最新的 session
        today = date.today()
        all_sessions = await session_repo.get_group_sessions(group_id, today, today)
        sessions = [all_sessions[0]] if all_sessions else []

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


@router.get("/groups/{group_id}/today-stores")
async def get_today_stores(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得今日店家"""
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
):
    """設定今日店家"""
    from app.services import CacheService
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


@router.get("/stores")
async def get_available_stores(
    db: AsyncSession = Depends(get_db),
):
    """取得可用店家列表"""
    repo = StoreRepository(db)
    stores = await repo.get_active_stores()

    return [
        {
            "id": str(store.id),
            "name": store.name,
            "phone": store.phone,
            "address": store.address,
        }
        for store in stores
    ]


@router.post("/orders/{order_id}/mark-paid")
async def mark_order_paid(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """標記訂單已付款（LINE 管理員用）"""
    from app.services import OrderService
    from app.broadcast import commit_and_notify

    service = OrderService(db)
    await service.mark_paid(order_id)
    await commit_and_notify(db)
    return {"success": True}


@router.post("/change-group-code")
async def change_group_code(
    data: ChangeGroupCode,
    db: AsyncSession = Depends(get_db),
):
    """變更群組代碼"""
    app_repo = GroupApplicationRepository(db)
    store_repo = StoreRepository(db)
    group_repo = GroupRepository(db)

    # 驗證目前代碼
    applications = await app_repo.get_approved_by_password(data.current_code)
    if not applications:
        raise HTTPException(status_code=401, detail="目前代碼錯誤")

    # 驗證新代碼長度
    if len(data.new_code) < 4 or len(data.new_code) > 20:
        raise HTTPException(
            status_code=400,
            detail="新代碼長度需為 4-20 字元",
        )

    # 更新所有使用此代碼的申請
    for app in applications:
        app.group_code = data.new_code
        await app_repo.update(app)

    # 更新所有使用此代碼的群組
    groups = await group_repo.get_all_by_code(data.current_code)
    for group in groups:
        group.group_code = data.new_code
        await group_repo.update(group)

    # 更新所有使用此代碼的店家
    stores = await store_repo.get_stores_by_scope("group", data.current_code)
    for store in stores:
        store.group_code = data.new_code
        await store_repo.update(store)

    await db.commit()
    return {"success": True}


# ===== Store Management (LINE Admin) =====


@router.get("/stores/by-code/{group_code}")
async def get_stores_for_group(
    group_code: str,
    db: AsyncSession = Depends(get_db),
):
    """取得群組可用的店家列表（全局 + 群組專屬）

    返回結果包含：
    - 所有 scope=global 的店家
    - 所有 scope=group 且 group_code 相符的店家
    - 包含停用的店家（管理介面需要顯示以便重新啟用）
    """
    repo = StoreRepository(db)
    # 管理介面需要顯示所有店家（包含停用），以便重新啟用
    stores = await repo.get_stores_for_group_code(group_code, include_inactive=True)

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
            "can_edit": store.scope == "group" and store.group_code == group_code,
        }
        for store in stores
    ]


@router.post("/stores/by-code/{group_code}")
async def create_store_for_group(
    group_code: str,
    data: StoreCreate,
    db: AsyncSession = Depends(get_db),
):
    """建立群組專屬店家

    自動設定：
    - scope = "group"
    - group_code = 傳入的 group_code
    - created_by_type = "line_admin"
    """
    from app.models.store import Store
    from app.broadcast import commit_and_notify, emit_store_change

    repo = StoreRepository(db)
    store = Store(
        **data.model_dump(),
        scope="group",
        group_code=group_code,
        created_by_type="line_admin",
    )
    store = await repo.create(store)

    # 廣播店家列表變更
    group = await get_group_by_code(db, group_code)
    if group:
        await emit_store_change(str(group.id), {
            "action": "store_created",
            "store_id": str(store.id),
            "store_name": store.name,
            "group_code": group_code,
        })

    await commit_and_notify(db)

    return {
        "id": str(store.id),
        "name": store.name,
        "scope": store.scope,
        "group_code": store.group_code,
    }


@router.put("/stores/by-code/{group_code}/{store_id}")
async def update_store_for_group(
    group_code: str,
    store_id: UUID,
    data: StoreUpdate,
    db: AsyncSession = Depends(get_db),
):
    """更新群組店家

    權限檢查：
    - 只能編輯 scope=group 且 group_code 相符的店家
    - 無法編輯 scope=global 的店家
    """
    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="店家不存在")

    # 權限檢查
    if not repo.can_edit_store(store, group_code):
        if store.scope == "global":
            raise HTTPException(status_code=403, detail="無權限編輯全局店家")
        else:
            raise HTTPException(status_code=403, detail="無權限編輯其他群組的店家")

    # 更新店家
    for key, value in data.model_dump(exclude_unset=True).items():
        setattr(store, key, value)

    await repo.update(store)

    # 廣播店家列表變更
    from app.broadcast import commit_and_notify, emit_store_change
    group = await get_group_by_code(db, group_code)
    if group:
        await emit_store_change(str(group.id), {
            "action": "store_updated",
            "store_id": str(store.id),
            "store_name": store.name,
            "group_code": group_code,
        })

    await commit_and_notify(db)

    return {"success": True}


@router.delete("/stores/by-code/{group_code}/{store_id}")
async def delete_store_for_group(
    group_code: str,
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """刪除群組店家（硬刪除）

    權限檢查：
    - 只能刪除 scope=group 且 group_code 相符的店家
    """
    from app.services import CacheService

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="店家不存在")

    # 權限檢查
    if not repo.can_edit_store(store, group_code):
        if store.scope == "global":
            raise HTTPException(status_code=403, detail="無權限刪除全局店家")
        else:
            raise HTTPException(status_code=403, detail="無權限刪除其他群組的店家")

    store_name = store.name  # 保存名稱用於廣播
    await db.delete(store)

    # 廣播店家列表變更
    from app.broadcast import commit_and_notify, emit_store_change
    group = await get_group_by_code(db, group_code)
    if group:
        await emit_store_change(str(group.id), {
            "action": "store_deleted",
            "store_id": str(store_id),
            "store_name": store_name,
            "group_code": group_code,
        })

    await commit_and_notify(db)
    CacheService.clear_menu(str(store_id))

    return {"success": True}


# ===== Menu Management (LINE Admin) =====


@router.get("/stores/by-code/{group_code}/{store_id}/menu")
async def get_store_menu(
    group_code: str,
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得店家菜單"""
    from app.services import MenuService

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="店家不存在")

    # 檢查是否有權限查看（全局店家或相同 group_code）
    if store.scope == "group" and store.group_code != group_code:
        raise HTTPException(status_code=403, detail="無權限查看此店家")

    service = MenuService(db)
    menu = await service.get_store_menu(store_id)
    return menu or {"categories": []}


@router.post("/menu/recognize")
async def recognize_menu_only(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """辨識菜單圖片（不需要指定店家，用於新增店家時）"""
    from app.services import MenuService

    service = MenuService(db)
    image_bytes = await file.read()
    result = await service.recognize_menu_image(image_bytes)
    return {"recognized_menu": result}


@router.post("/stores/by-code/{group_code}/{store_id}/menu/recognize")
async def recognize_menu_for_group(
    group_code: str,
    store_id: UUID,
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
):
    """辨識菜單圖片並與現有菜單比對"""
    from app.services import MenuService

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="店家不存在")

    # 權限檢查（只能為群組店家上傳菜單）
    if not repo.can_edit_store(store, group_code):
        if store.scope == "global":
            raise HTTPException(status_code=403, detail="無權限編輯全局店家菜單")
        else:
            raise HTTPException(status_code=403, detail="無權限編輯其他群組的店家菜單")

    service = MenuService(db)

    # 辨識新菜單
    image_bytes = await file.read()
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


@router.post("/stores/by-code/{group_code}/{store_id}/menu")
async def save_menu_for_group(
    group_code: str,
    store_id: UUID,
    data: MenuSave,
    db: AsyncSession = Depends(get_db),
):
    """儲存菜單（完整覆蓋）"""
    from app.services import MenuService

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="店家不存在")

    # 權限檢查
    if not repo.can_edit_store(store, group_code):
        if store.scope == "global":
            raise HTTPException(status_code=403, detail="無權限編輯全局店家菜單")
        else:
            raise HTTPException(status_code=403, detail="無權限編輯其他群組的店家菜單")

    # 更新店家資訊（如果有提供）
    store_info_updated = False
    if data.store_info:
        store_info = data.store_info
        if store_info.name:
            store.name = store_info.name
        if store_info.phone is not None:
            store.phone = store_info.phone
        if store_info.address is not None:
            store.address = store_info.address
        if store_info.description is not None:
            store.description = store_info.description
        await repo.update(store)
        store_info_updated = True

    service = MenuService(db)
    menu = await service.save_menu(store_id, data.categories)

    # 提交變更
    await db.commit()

    # 如果有更新店家資訊，發送 socket 事件
    if store_info_updated:
        from app.broadcast import emit_store_change
        group = await get_group_by_code(db, group_code)
        if group:
            await emit_store_change(str(group.id), {
                "action": "store_updated",
                "store_id": str(store.id),
                "store_name": store.name,
                "group_code": group_code,
            })

    return {"success": True, "menu_id": str(menu.id)}


@router.post("/stores/by-code/{group_code}/{store_id}/menu/save")
async def save_menu_diff_for_group(
    group_code: str,
    store_id: UUID,
    data: MenuSaveDiff,
    db: AsyncSession = Depends(get_db),
):
    """儲存菜單（支援差異模式）"""
    from app.services import MenuService

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="店家不存在")

    # 權限檢查
    if not repo.can_edit_store(store, group_code):
        if store.scope == "global":
            raise HTTPException(status_code=403, detail="無權限編輯全局店家菜單")
        else:
            raise HTTPException(status_code=403, detail="無權限編輯其他群組的店家菜單")

    # 更新店家資訊（如果有提供）
    store_info_updated = False
    if data.store_info:
        store_info = data.store_info
        if store_info.name:
            store.name = store_info.name
        if store_info.phone is not None:
            store.phone = store_info.phone
        if store_info.address is not None:
            store.address = store_info.address
        if store_info.description is not None:
            store.description = store_info.description
        await repo.update(store)
        store_info_updated = True

    service = MenuService(db)

    if not data.diff_mode:
        # 完整覆蓋模式
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

    # 如果有更新店家資訊，發送 socket 事件
    if store_info_updated:
        from app.broadcast import emit_store_change
        group = await get_group_by_code(db, group_code)
        if group:
            await emit_store_change(str(group.id), {
                "action": "store_updated",
                "store_id": str(store.id),
                "store_name": store.name,
                "group_code": group_code,
            })

    return {"success": True, "menu_id": str(menu.id)}


@router.get("/stores/by-code/{group_code}/{store_id}/menu/compare")
async def compare_menu_for_group(
    group_code: str,
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得現有菜單（用於比較）"""
    from app.services import MenuService

    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)

    if not store:
        raise HTTPException(status_code=404, detail="店家不存在")

    # 檢查是否有權限查看（全局店家或相同 group_code）
    if store.scope == "group" and store.group_code != group_code:
        raise HTTPException(status_code=403, detail="無權限查看此店家")

    service = MenuService(db)
    menu = await service.get_store_menu(store_id)
    return menu or {"categories": []}
