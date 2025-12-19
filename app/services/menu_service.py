"""菜單服務"""
import io
import logging
from typing import List, Optional
from uuid import UUID

from PIL import Image
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.menu import Menu, MenuCategory, MenuItem
from app.models.store import Store
from app.repositories import (
    StoreRepository,
    MenuRepository,
    MenuCategoryRepository,
    MenuItemRepository,
    AiPromptRepository,
)
from app.services.ai_service import AiService
from app.services.cache_service import CacheService

logger = logging.getLogger("jaba.menu")


class MenuService:
    """菜單服務"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.store_repo = StoreRepository(session)
        self.menu_repo = MenuRepository(session)
        self.category_repo = MenuCategoryRepository(session)
        self.item_repo = MenuItemRepository(session)
        self.ai_service = AiService()

    async def get_store_menu(self, store_id: UUID) -> Optional[dict]:
        """取得店家菜單"""
        # 檢查快取
        cache_key = str(store_id)
        cached = CacheService.get_menu(cache_key)
        if cached:
            return cached

        # 從資料庫取得
        store = await self.store_repo.get_with_menu(store_id)
        if not store or not store.menu:
            return None

        menu_data = self._serialize_menu(store.menu)

        # 存入快取
        CacheService.set_menu(cache_key, menu_data)

        return menu_data

    def _serialize_menu(self, menu: Menu) -> dict:
        """序列化菜單"""
        return {
            "id": str(menu.id),
            "store_id": str(menu.store_id),
            "categories": [
                {
                    "id": str(cat.id),
                    "name": cat.name,
                    "sort_order": cat.sort_order,
                    "items": [
                        {
                            "id": str(item.id),
                            "name": item.name,
                            "price": float(item.price),
                            "description": item.description,
                            "is_available": item.is_available,
                            "variants": item.variants,
                            "promo": item.promo,
                            "sort_order": item.sort_order,
                        }
                        for item in sorted(cat.items, key=lambda x: x.sort_order)
                    ],
                }
                for cat in sorted(menu.categories, key=lambda x: x.sort_order)
            ],
        }

    async def recognize_menu_image(self, image_bytes: bytes) -> dict:
        """辨識菜單圖片"""
        # 確保 prompt 已載入到快取
        await self._ensure_prompt_cached("menu_recognition")

        # 壓縮圖片
        compressed = self._compress_image(image_bytes)

        # 直接傳 bytes 給 AI 服務
        return await self.ai_service.recognize_menu(compressed)

    async def _ensure_prompt_cached(self, name: str) -> None:
        """確保 prompt 已載入到快取"""
        if CacheService.get_prompt(name):
            return

        # 從 DB 載入
        prompt_repo = AiPromptRepository(self.session)
        prompt = await prompt_repo.get_by_name(name)
        if prompt:
            CacheService.set_prompt(name, prompt.content)

    def _compress_image(
        self, image_bytes: bytes, max_size: int = 1920, quality: int = 85
    ) -> bytes:
        """
        壓縮圖片（用於 AI 辨識）

        智能檢查：如果圖片檔案 < 500KB 且尺寸 <= max_size，跳過壓縮避免品質損失
        """
        try:
            img = Image.open(io.BytesIO(image_bytes))
            original_size = len(image_bytes)
            needs_resize = max(img.size) > max_size
            needs_convert = img.mode in ("RGBA", "P")

            # 智能檢查：檔案已經夠小且尺寸合適，跳過壓縮
            if original_size < 500 * 1024 and not needs_resize and not needs_convert:
                logger.debug(
                    f"圖片已壓縮，跳過處理 (size={original_size}, dimensions={img.size})"
                )
                return image_bytes

            # 轉換為 RGB（如果是 RGBA）
            if needs_convert:
                img = img.convert("RGB")

            # 保持比例縮放
            if needs_resize:
                ratio = max_size / max(img.size)
                new_size = (int(img.size[0] * ratio), int(img.size[1] * ratio))
                img = img.resize(new_size, Image.Resampling.LANCZOS)

            # 輸出為 JPEG
            output = io.BytesIO()
            img.save(output, format="JPEG", quality=quality)
            compressed = output.getvalue()

            logger.debug(
                f"圖片壓縮完成: {original_size} → {len(compressed)} bytes"
            )
            return compressed

        except Exception as e:
            logger.error(f"Image compression error: {e}")
            return image_bytes

    async def save_menu(
        self, store_id: UUID, categories_data: List[dict]
    ) -> Menu:
        """
        儲存菜單

        categories_data: [
            {
                "name": "分類名稱",
                "items": [
                    {
                        "name": "品項名稱",
                        "price": 100,
                        "description": "描述",
                        "variants": [{"name": "M", "price": 50}],
                        "promo": {"type": "discount", "label": "買一送一", "value": 50}
                    }
                ]
            }
        ]
        """
        # 取得或建立菜單
        menu = await self.menu_repo.get_or_create(store_id)

        # 刪除現有分類和品項
        for category in menu.categories:
            await self.category_repo.delete(category)

        # 建立新分類和品項
        for sort_order, cat_data in enumerate(categories_data):
            category = MenuCategory(
                menu_id=menu.id,
                name=cat_data["name"],
                sort_order=sort_order,
            )
            category = await self.category_repo.create(category)

            for item_order, item_data in enumerate(cat_data.get("items", [])):
                item = MenuItem(
                    category_id=category.id,
                    name=item_data["name"],
                    price=item_data["price"],
                    description=item_data.get("description"),
                    variants=item_data.get("variants", []),
                    promo=item_data.get("promo"),
                    sort_order=item_order,
                )
                await self.item_repo.create(item)

        # 清除快取
        CacheService.clear_menu(str(store_id))

        # 重新載入菜單
        await self.session.refresh(menu, ["categories"])
        return menu

    async def delete_menu(self, store_id: UUID) -> bool:
        """刪除店家的菜單"""
        store = await self.store_repo.get_with_menu(store_id)
        if not store or not store.menu:
            return False

        # 刪除菜單（會連帶刪除分類和品項）
        await self.session.delete(store.menu)
        await self.session.commit()

        # 清除快取
        CacheService.clear_menu(str(store_id))
        return True

    async def save_menu_diff(
        self,
        store_id: UUID,
        apply_items: List[dict],
        remove_items: List[str],
    ) -> Menu:
        """
        選擇性儲存菜單（差異模式）

        Args:
            store_id: 店家 ID
            apply_items: 要套用的品項清單 [{"name": "xxx", "price": 100, "category": "分類", ...}]
            remove_items: 要刪除的品項名稱清單（正規化後的名稱）
        """
        # 取得現有菜單
        existing_menu = await self.get_store_menu(store_id)
        if not existing_menu:
            # 沒有現有菜單，直接建立
            categories_data = self._group_items_by_category(apply_items)
            return await self.save_menu(store_id, categories_data)

        # 建立現有品項索引
        existing_by_key = {}
        for cat in existing_menu.get("categories", []):
            for item in cat.get("items", []):
                key = self._normalize_name(item["name"])
                existing_by_key[key] = {
                    "category": cat["name"],
                    **item,
                }

        # 移除指定品項
        for key in remove_items:
            normalized_key = self._normalize_name(key)
            if normalized_key in existing_by_key:
                del existing_by_key[normalized_key]

        # 套用新品項（新增或修改）
        for item in apply_items:
            key = self._normalize_name(item["name"])
            existing_by_key[key] = item

        # 重組成分類結構
        categories_data = self._group_items_by_category(list(existing_by_key.values()))

        return await self.save_menu(store_id, categories_data)

    def _group_items_by_category(self, items: List[dict]) -> List[dict]:
        """將品項依分類分組"""
        categories = {}
        for item in items:
            cat_name = item.get("category", "未分類")
            if cat_name not in categories:
                categories[cat_name] = {"name": cat_name, "items": []}
            # 移除 category 欄位（儲存時不需要）
            item_data = {k: v for k, v in item.items() if k != "category"}
            categories[cat_name]["items"].append(item_data)

        return list(categories.values())

    def compare_menus(self, old_menu: dict, new_menu: dict) -> dict:
        """
        比較新舊菜單差異

        Returns:
            {
                "added": [...],
                "modified": [...],
                "unchanged": [...],
                "removed": [...]
            }
        """
        # 建立舊菜單品項索引（正規化名稱為 key）
        old_items = {}
        for cat in old_menu.get("categories", []):
            for item in cat.get("items", []):
                key = self._normalize_name(item["name"])
                old_items[key] = {
                    "category": cat["name"],
                    **item,
                }

        # 建立新菜單品項索引
        new_items = {}
        for cat in new_menu.get("categories", []):
            for item in cat.get("items", []):
                key = self._normalize_name(item["name"])
                new_items[key] = {
                    "category": cat["name"],
                    **item,
                }

        # 比較
        added = []
        modified = []
        unchanged = []
        removed = []

        for key, new_item in new_items.items():
            if key not in old_items:
                added.append(new_item)
            else:
                old_item = old_items[key]
                if self._items_differ(old_item, new_item):
                    modified.append({
                        "old": old_item,
                        "new": new_item,
                        "changes": self._get_item_changes(old_item, new_item),
                    })
                else:
                    unchanged.append(new_item)

        for key, old_item in old_items.items():
            if key not in new_items:
                removed.append(old_item)

        return {
            "added": added,
            "modified": modified,
            "unchanged": unchanged,
            "removed": removed,
        }

    def _normalize_name(self, name: str) -> str:
        """正規化品項名稱（去除空白和標點）"""
        import re
        return re.sub(r"[\s\W]", "", name.lower())

    def _items_differ(self, old_item: dict, new_item: dict) -> bool:
        """比較兩個品項是否不同"""
        # 比較價格
        if old_item.get("price") != new_item.get("price"):
            return True

        # 比較變體
        old_variants = sorted(
            old_item.get("variants", []),
            key=lambda x: x.get("name", ""),
        )
        new_variants = sorted(
            new_item.get("variants", []),
            key=lambda x: x.get("name", ""),
        )
        if old_variants != new_variants:
            return True

        # 比較促銷
        if old_item.get("promo") != new_item.get("promo"):
            return True

        return False

    def _get_item_changes(self, old_item: dict, new_item: dict) -> list:
        """取得品項的變更詳情"""
        changes = []

        # 價格變更
        if old_item.get("price") != new_item.get("price"):
            changes.append(f"價格 ${old_item.get('price')} → ${new_item.get('price')}")

        # 變體變更
        old_variants = {v.get("name"): v.get("price") for v in (old_item.get("variants") or [])}
        new_variants = {v.get("name"): v.get("price") for v in (new_item.get("variants") or [])}
        if old_variants != new_variants:
            changes.append("尺寸價格變更")

        # 促銷變更
        if old_item.get("promo") != new_item.get("promo"):
            old_label = (old_item.get("promo") or {}).get("label", "無")
            new_label = (new_item.get("promo") or {}).get("label", "無")
            changes.append(f"促銷 {old_label} → {new_label}")

        return changes
