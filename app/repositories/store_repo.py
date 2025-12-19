"""店家 Repository"""
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, or_, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.store import Store
from app.models.menu import Menu, MenuCategory, MenuItem
from app.repositories.base import BaseRepository


class StoreRepository(BaseRepository[Store]):
    """店家 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(Store, session)

    async def get_active_stores(self) -> List[Store]:
        """取得所有啟用的店家"""
        result = await self.session.execute(
            select(Store)
            .where(Store.is_active == True)
            .order_by(Store.name)
        )
        return list(result.scalars().all())

    async def get_all_stores(self) -> List[Store]:
        """取得所有店家（包含停用）"""
        result = await self.session.execute(
            select(Store).order_by(Store.name)
        )
        return list(result.scalars().all())

    async def get_with_menu(self, store_id: UUID) -> Optional[Store]:
        """取得店家及其菜單"""
        result = await self.session.execute(
            select(Store)
            .where(Store.id == store_id)
            .options(
                selectinload(Store.menu)
                .selectinload(Menu.categories)
                .selectinload(MenuCategory.items)
            )
        )
        return result.scalar_one_or_none()

    async def search_by_name(self, name: str) -> List[Store]:
        """根據名稱搜尋店家"""
        result = await self.session.execute(
            select(Store)
            .where(Store.name.ilike(f"%{name}%"))
            .order_by(Store.name)
        )
        return list(result.scalars().all())

    async def get_stores_for_group_code(
        self, group_code: str, include_inactive: bool = False
    ) -> List[Store]:
        """取得群組可用的店家（全局 + 相同 group_code 的群組店家）

        Args:
            group_code: 群組代碼
            include_inactive: 是否包含停用的店家（管理介面用）
        """
        conditions = [
            or_(
                Store.scope == "global",
                and_(
                    Store.scope == "group",
                    Store.group_code == group_code
                )
            )
        ]

        # 預設只顯示啟用的店家（給 LINE Bot 使用）
        if not include_inactive:
            conditions.append(Store.is_active == True)

        result = await self.session.execute(
            select(Store)
            .where(*conditions)
            .order_by(Store.name)
        )
        return list(result.scalars().all())

    async def get_stores_by_scope(
        self, scope: str, group_code: Optional[str] = None
    ) -> List[Store]:
        """依 scope 篩選店家"""
        conditions = [Store.scope == scope]
        if scope == "group" and group_code:
            conditions.append(Store.group_code == group_code)

        result = await self.session.execute(
            select(Store)
            .where(*conditions)
            .order_by(Store.name)
        )
        return list(result.scalars().all())

    def can_edit_store(self, store: Store, group_code: Optional[str]) -> bool:
        """檢查是否有權限編輯店家

        - 全局店家 (scope=global): 只有超管可編輯（呼叫端需判斷）
        - 群組店家 (scope=group): 只有相同 group_code 的 LINE 管可編輯

        Returns:
            True: 有權限（需進一步檢查 group_code）
            False: 無權限
        """
        if store.scope == "global":
            # 全局店家 - LINE 管理員無法編輯
            return False

        if store.scope == "group":
            # 群組店家 - 只有相同 group_code 可編輯
            return store.group_code == group_code

        return False


class MenuRepository(BaseRepository[Menu]):
    """菜單 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(Menu, session)

    async def get_by_store_id(self, store_id: UUID) -> Optional[Menu]:
        """根據店家 ID 取得菜單"""
        result = await self.session.execute(
            select(Menu)
            .where(Menu.store_id == store_id)
            .options(
                selectinload(Menu.categories).selectinload(MenuCategory.items)
            )
        )
        return result.scalar_one_or_none()

    async def get_or_create(self, store_id: UUID) -> Menu:
        """取得或建立菜單"""
        menu = await self.get_by_store_id(store_id)
        if menu is None:
            menu = Menu(store_id=store_id)
            menu = await self.create(menu)
            # 重新載入以確保 categories 關聯正確初始化
            menu = await self.get_by_store_id(store_id)
        return menu


class MenuCategoryRepository(BaseRepository[MenuCategory]):
    """菜單分類 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(MenuCategory, session)


class MenuItemRepository(BaseRepository[MenuItem]):
    """菜單品項 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(MenuItem, session)

    async def search_by_name(
        self, menu_id: UUID, name: str
    ) -> List[MenuItem]:
        """根據名稱搜尋品項"""
        result = await self.session.execute(
            select(MenuItem)
            .join(MenuCategory)
            .where(
                MenuCategory.menu_id == menu_id,
                MenuItem.name.ilike(f"%{name}%"),
                MenuItem.is_available == True,
            )
        )
        return list(result.scalars().all())
