"""系統設定 Repository"""
import hashlib
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.system import AiPrompt, SecurityLog, SuperAdmin
from app.repositories.base import BaseRepository


def hash_password(password: str) -> str:
    """簡單的密碼 hash（生產環境建議用 bcrypt）"""
    return hashlib.sha256(password.encode()).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    """驗證密碼"""
    return hash_password(password) == password_hash


class SuperAdminRepository:
    """超級管理員 Repository"""

    def __init__(self, session: AsyncSession):
        self.session = session

    async def get_by_username(self, username: str) -> Optional[SuperAdmin]:
        """根據使用者名稱取得管理員"""
        result = await self.session.execute(
            select(SuperAdmin).where(SuperAdmin.username == username)
        )
        return result.scalar_one_or_none()

    async def create(self, username: str, password: str) -> SuperAdmin:
        """建立管理員"""
        admin = SuperAdmin(
            username=username,
            password_hash=hash_password(password)
        )
        self.session.add(admin)
        await self.session.flush()
        return admin

    async def verify_credentials(self, username: str, password: str) -> Optional[SuperAdmin]:
        """驗證帳號密碼"""
        admin = await self.get_by_username(username)
        if admin and verify_password(password, admin.password_hash):
            return admin
        return None

    async def count(self) -> int:
        """取得管理員數量"""
        from sqlalchemy import func as sql_func
        result = await self.session.execute(
            select(sql_func.count()).select_from(SuperAdmin)
        )
        return result.scalar() or 0

    async def get_all(self) -> List[SuperAdmin]:
        """取得所有管理員"""
        result = await self.session.execute(
            select(SuperAdmin).order_by(SuperAdmin.username)
        )
        return list(result.scalars().all())

    async def update_password(self, username: str, new_password: str) -> Optional[SuperAdmin]:
        """更新密碼"""
        admin = await self.get_by_username(username)
        if admin:
            admin.password_hash = hash_password(new_password)
            await self.session.flush()
        return admin

    async def delete(self, username: str) -> bool:
        """刪除管理員"""
        admin = await self.get_by_username(username)
        if admin:
            await self.session.delete(admin)
            await self.session.flush()
            return True
        return False


class AiPromptRepository(BaseRepository[AiPrompt]):
    """AI 提示詞 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(AiPrompt, session)

    async def get_by_name(self, name: str) -> Optional[AiPrompt]:
        """根據名稱取得提示詞"""
        result = await self.session.execute(
            select(AiPrompt).where(AiPrompt.name == name)
        )
        return result.scalar_one_or_none()

    async def get_all_prompts(self) -> List[AiPrompt]:
        """取得所有提示詞"""
        result = await self.session.execute(
            select(AiPrompt).order_by(AiPrompt.name)
        )
        return list(result.scalars().all())

    async def set_prompt(self, name: str, content: str) -> AiPrompt:
        """設定提示詞"""
        prompt = await self.get_by_name(name)
        if prompt is None:
            prompt = AiPrompt(name=name, content=content)
            prompt = await self.create(prompt)
        else:
            prompt.content = content
            prompt = await self.update(prompt)
        return prompt


class SecurityLogRepository(BaseRepository[SecurityLog]):
    """安全日誌 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(SecurityLog, session)

    async def get_recent(
        self,
        limit: int = 50,
        offset: int = 0,
        line_user_id: Optional[str] = None,
        line_group_id: Optional[str] = None,
    ) -> List[SecurityLog]:
        """取得最近的安全日誌"""
        query = select(SecurityLog)

        if line_user_id:
            query = query.where(SecurityLog.line_user_id == line_user_id)
        if line_group_id:
            query = query.where(SecurityLog.line_group_id == line_group_id)

        query = query.order_by(SecurityLog.created_at.desc()).offset(offset).limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())

    async def get_total_count(
        self,
        line_user_id: Optional[str] = None,
        line_group_id: Optional[str] = None,
    ) -> int:
        """取得日誌總數"""
        from sqlalchemy import func as sql_func

        query = select(sql_func.count()).select_from(SecurityLog)

        if line_user_id:
            query = query.where(SecurityLog.line_user_id == line_user_id)
        if line_group_id:
            query = query.where(SecurityLog.line_group_id == line_group_id)

        result = await self.session.execute(query)
        return result.scalar() or 0

    async def get_stats(self) -> dict:
        """取得統計資訊"""
        from datetime import timedelta
        from sqlalchemy import func as sql_func, cast, Date

        # 總數
        total = await self.get_total_count()

        # 依觸發原因統計（使用 JSONB 展開）
        # 簡化處理：取得最近 1000 筆統計
        recent_logs = await self.get_recent(limit=1000)
        reason_counts: dict[str, int] = {}
        for log in recent_logs:
            for reason in log.trigger_reasons:
                reason_counts[reason] = reason_counts.get(reason, 0) + 1

        # 最近 7 天每日統計
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc)
        seven_days_ago = now - timedelta(days=7)

        daily_query = (
            select(
                cast(SecurityLog.created_at, Date).label("date"),
                sql_func.count().label("count"),
            )
            .where(SecurityLog.created_at >= seven_days_ago)
            .group_by(cast(SecurityLog.created_at, Date))
            .order_by(cast(SecurityLog.created_at, Date))
        )
        daily_result = await self.session.execute(daily_query)
        daily_stats = [{"date": str(row.date), "count": row.count} for row in daily_result]

        return {
            "total": total,
            "by_reason": reason_counts,
            "daily": daily_stats,
        }
