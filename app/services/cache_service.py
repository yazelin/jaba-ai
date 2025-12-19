"""快取服務 - 使用記憶體 dict"""
from typing import Any, Optional

# 全域快取
_menu_cache: dict[str, Any] = {}
_today_stores_cache: dict[str, Any] = {}
_prompt_cache: dict[str, str] = {}


class CacheService:
    """快取服務"""

    # Menu Cache
    @staticmethod
    def get_menu(store_id: str) -> Optional[Any]:
        """取得菜單快取"""
        return _menu_cache.get(store_id)

    @staticmethod
    def set_menu(store_id: str, menu: Any) -> None:
        """設定菜單快取"""
        _menu_cache[store_id] = menu

    @staticmethod
    def clear_menu(store_id: str) -> None:
        """清除菜單快取"""
        _menu_cache.pop(store_id, None)

    @staticmethod
    def clear_all_menus() -> None:
        """清除所有菜單快取"""
        _menu_cache.clear()

    # Today Stores Cache
    @staticmethod
    def get_today_stores(group_id: str) -> Optional[Any]:
        """取得今日店家快取"""
        return _today_stores_cache.get(group_id)

    @staticmethod
    def set_today_stores(group_id: str, stores: Any) -> None:
        """設定今日店家快取"""
        _today_stores_cache[group_id] = stores

    @staticmethod
    def clear_today_stores(group_id: str) -> None:
        """清除今日店家快取"""
        _today_stores_cache.pop(group_id, None)

    @staticmethod
    def clear_all_today_stores() -> None:
        """清除所有今日店家快取"""
        _today_stores_cache.clear()

    # Prompt Cache
    @staticmethod
    def get_prompt(name: str) -> Optional[str]:
        """取得提示詞快取"""
        return _prompt_cache.get(name)

    @staticmethod
    def set_prompt(name: str, content: str) -> None:
        """設定提示詞快取"""
        _prompt_cache[name] = content

    @staticmethod
    def clear_prompt(name: str) -> None:
        """清除提示詞快取"""
        _prompt_cache.pop(name, None)

    @staticmethod
    def clear_all_prompts() -> None:
        """清除所有提示詞快取"""
        _prompt_cache.clear()

    # Clear All
    @staticmethod
    def clear_all() -> None:
        """清除所有快取"""
        _menu_cache.clear()
        _today_stores_cache.clear()
        _prompt_cache.clear()
