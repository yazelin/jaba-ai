"""對話記錄 Repository"""
from datetime import date, datetime, timedelta
from typing import List, Optional, Tuple
from uuid import UUID
import zoneinfo

from sqlalchemy import select, func, and_, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.chat import ChatMessage
from app.repositories.base import BaseRepository

# 台北時區
TW_TZ = zoneinfo.ZoneInfo("Asia/Taipei")


def get_today_tw() -> date:
    """取得台北時區的今日日期"""
    return datetime.now(TW_TZ).date()


class ChatRepository(BaseRepository[ChatMessage]):
    """對話記錄 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(ChatMessage, session)

    async def get_group_messages(
        self,
        group_id: UUID,
        limit: int = 50,
        session_id: Optional[UUID] = None,
        today_only: bool = True,
    ) -> List[ChatMessage]:
        """取得群組對話記錄

        Args:
            group_id: 群組 ID
            limit: 最多回傳筆數
            session_id: 點餐 Session ID（可選）
            today_only: 是否只取今日對話（預設 True）
        """
        query = select(ChatMessage).where(ChatMessage.group_id == group_id)

        if session_id:
            query = query.where(ChatMessage.session_id == session_id)

        if today_only:
            today = get_today_tw()
            query = query.where(func.date(ChatMessage.created_at) == today)

        # 載入 user 關聯以取得用戶名稱
        query = query.options(selectinload(ChatMessage.user))
        query = query.order_by(ChatMessage.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        return list(reversed(messages))  # 回傳時間順序

    async def delete_group_messages(self, group_id: UUID) -> int:
        """刪除群組所有對話記錄（用於重新申請時清除舊對話）

        Returns:
            刪除的記錄數
        """
        from sqlalchemy import delete
        result = await self.session.execute(
            delete(ChatMessage).where(ChatMessage.group_id == group_id)
        )
        await self.session.flush()
        return result.rowcount

    async def get_user_messages(
        self,
        user_id: UUID,
        limit: int = 30,
        today_only: bool = True,
    ) -> List[ChatMessage]:
        """取得使用者個人對話記錄

        Args:
            user_id: 使用者 ID
            limit: 最多回傳筆數
            today_only: 是否只取今日對話（預設 True）
        """
        query = select(ChatMessage).where(
            ChatMessage.user_id == user_id,
            ChatMessage.group_id == None,  # 個人對話沒有群組
        )

        if today_only:
            today = get_today_tw()
            query = query.where(func.date(ChatMessage.created_at) == today)

        query = query.order_by(ChatMessage.created_at.desc()).limit(limit)

        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def add_message(
        self,
        role: str,
        content: str,
        group_id: Optional[UUID] = None,
        user_id: Optional[UUID] = None,
        session_id: Optional[UUID] = None,
    ) -> ChatMessage:
        """新增對話記錄"""
        message = ChatMessage(
            role=role,
            content=content,
            group_id=group_id,
            user_id=user_id,
            session_id=session_id,
        )
        return await self.create(message)

    async def get_today_messages(
        self,
        group_id: Optional[UUID] = None,
        limit: int = 100,
    ) -> List[ChatMessage]:
        """取得今日對話記錄（用於看板）"""
        today = get_today_tw()

        query = select(ChatMessage).where(
            func.date(ChatMessage.created_at) == today
        )

        if group_id:
            query = query.where(ChatMessage.group_id == group_id)
        else:
            query = query.where(ChatMessage.group_id != None)  # 只要群組對話

        query = (
            query.options(selectinload(ChatMessage.user))
            .order_by(ChatMessage.created_at.desc())
            .limit(limit)
        )

        result = await self.session.execute(query)
        messages = list(result.scalars().all())
        return list(reversed(messages))

    async def clear_session_messages(self, session_id: UUID) -> None:
        """清除 Session 的對話記錄"""
        result = await self.session.execute(
            select(ChatMessage).where(ChatMessage.session_id == session_id)
        )
        for message in result.scalars().all():
            await self.session.delete(message)
        await self.session.flush()

    async def count_old_messages(self, retention_days: int = 365) -> int:
        """計算超過保留天數的訊息數量"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)
        result = await self.session.execute(
            select(func.count(ChatMessage.id)).where(
                ChatMessage.created_at < cutoff_date
            )
        )
        return result.scalar() or 0

    async def cleanup_old_messages(self, retention_days: int = 365) -> int:
        """清理超過保留天數的訊息，回傳刪除筆數"""
        cutoff_date = datetime.now() - timedelta(days=retention_days)

        # 先計算數量
        count = await self.count_old_messages(retention_days)

        if count > 0:
            # 批次刪除
            await self.session.execute(
                delete(ChatMessage).where(ChatMessage.created_at < cutoff_date)
            )
            await self.session.flush()

        return count

    async def get_stats(self) -> dict:
        """取得對話統計資訊"""
        # 總數
        total_result = await self.session.execute(
            select(func.count(ChatMessage.id))
        )
        total = total_result.scalar() or 0

        # 超過一年的數量
        old_count = await self.count_old_messages(365)

        # 最舊的訊息日期
        oldest_result = await self.session.execute(
            select(func.min(ChatMessage.created_at))
        )
        oldest = oldest_result.scalar()

        return {
            "total_messages": total,
            "messages_older_than_1_year": old_count,
            "oldest_message_date": oldest.isoformat() if oldest else None,
        }
