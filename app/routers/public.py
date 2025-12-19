"""公開 API 路由"""
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.repositories import StoreRepository, GroupTodayStoreRepository
from app.services import MenuService

router = APIRouter(prefix="/api/public", tags=["public"])


@router.get("/stores")
async def get_stores(
    active_only: bool = True,
    db: AsyncSession = Depends(get_db),
):
    """取得店家列表"""
    repo = StoreRepository(db)
    if active_only:
        stores = await repo.get_active_stores()
    else:
        stores = await repo.get_all_stores()

    return [
        {
            "id": str(store.id),
            "name": store.name,
            "phone": store.phone,
            "address": store.address,
            "description": store.description,
            "is_active": store.is_active,
        }
        for store in stores
    ]


@router.get("/stores/{store_id}")
async def get_store(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得店家詳情"""
    repo = StoreRepository(db)
    store = await repo.get_by_id(store_id)
    if not store:
        raise HTTPException(status_code=404, detail="Store not found")

    return {
        "id": str(store.id),
        "name": store.name,
        "phone": store.phone,
        "address": store.address,
        "description": store.description,
        "note": store.note,
        "is_active": store.is_active,
    }


@router.get("/menu/{store_id}")
async def get_menu(
    store_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得店家菜單"""
    service = MenuService(db)
    menu = await service.get_store_menu(store_id)
    if not menu:
        raise HTTPException(status_code=404, detail="Menu not found")
    return menu


@router.get("/today/{group_id}")
async def get_today_stores(
    group_id: UUID,
    db: AsyncSession = Depends(get_db),
):
    """取得群組今日店家"""
    repo = GroupTodayStoreRepository(db)
    today_stores = await repo.get_today_stores(group_id)

    return [
        {
            "store_id": str(ts.store_id),
            "store_name": ts.store.name if ts.store else None,
            "date": str(ts.date),
        }
        for ts in today_stores
    ]


@router.get("/linebot-status")
async def get_linebot_status():
    """檢查 LINE Bot 運行狀態"""
    # 檢查 LINE 設定是否完整
    has_secret = bool(settings.line_channel_secret)
    has_token = bool(settings.line_channel_access_token)

    if has_secret and has_token:
        return {"status": "online", "message": "LINE Bot 運行中"}
    elif has_secret or has_token:
        return {"status": "offline", "message": "LINE 設定不完整"}
    else:
        return {"status": "offline", "message": "LINE 尚未設定"}
