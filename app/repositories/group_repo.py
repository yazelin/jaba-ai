"""群組 Repository"""
from datetime import datetime
from typing import List, Optional, Tuple
from uuid import UUID

from sqlalchemy import select, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.group import Group, GroupAdmin, GroupApplication, GroupMember
from app.repositories.base import BaseRepository


class GroupRepository(BaseRepository[Group]):
    """群組 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(Group, session)

    async def get_by_line_group_id(self, line_group_id: str) -> Optional[Group]:
        """根據 LINE Group ID 取得群組"""
        result = await self.session.execute(
            select(Group).where(Group.line_group_id == line_group_id)
        )
        return result.scalar_one_or_none()

    async def get_by_code(self, group_code: str) -> Optional[Group]:
        """根據群組代碼取得群組（回傳第一個符合的）"""
        result = await self.session.execute(
            select(Group).where(
                Group.group_code == group_code,
                Group.status == "active"
            )
        )
        return result.scalar_one_or_none()

    async def get_all_by_code(self, group_code: str) -> List[Group]:
        """根據群組代碼取得所有群組"""
        result = await self.session.execute(
            select(Group).where(
                Group.group_code == group_code,
                Group.status == "active"
            )
        )
        return list(result.scalars().all())

    async def get_active_groups(self) -> List[Group]:
        """取得所有已啟用的群組"""
        result = await self.session.execute(
            select(Group).where(Group.status == "active")
        )
        return list(result.scalars().all())

    async def get_or_create(
        self, line_group_id: str, name: Optional[str] = None
    ) -> Group:
        """取得或建立群組"""
        group = await self.get_by_line_group_id(line_group_id)
        if group is None:
            group = Group(line_group_id=line_group_id, name=name, status="pending")
            group = await self.create(group)
        return group

    async def activate(self, group: Group, activated_by: UUID) -> Group:
        """啟用群組"""
        group.status = "active"
        group.activated_at = datetime.now()
        group.activated_by = activated_by
        return await self.update(group)

    async def get_all_paginated(
        self,
        limit: int = 20,
        offset: int = 0,
        search: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Tuple[List[Group], int]:
        """分頁取得群組列表

        Args:
            limit: 每頁數量
            offset: 偏移量
            search: 搜尋關鍵字（名稱或代碼）
            status: 狀態篩選（all/active/suspended/pending）

        Returns:
            (群組列表, 總數)
        """
        query = select(Group)

        # 搜尋條件
        if search:
            search_pattern = f"%{search}%"
            query = query.where(
                or_(
                    Group.name.ilike(search_pattern),
                    Group.group_code.ilike(search_pattern),
                    Group.line_group_id.ilike(search_pattern),
                )
            )

        # 狀態篩選
        if status and status != "all":
            query = query.where(Group.status == status)

        # 計算總數
        count_query = select(func.count()).select_from(query.subquery())
        total = (await self.session.execute(count_query)).scalar() or 0

        # 取得分頁資料
        query = query.order_by(Group.created_at.desc()).limit(limit).offset(offset)
        result = await self.session.execute(query)
        groups = list(result.scalars().all())

        return groups, total

    async def get_group_with_stats(self, group_id: UUID) -> Optional[dict]:
        """取得群組詳情含統計資訊"""
        group = await self.get_by_id(group_id)
        if not group:
            return None

        # 取得成員數
        member_count_result = await self.session.execute(
            select(func.count(GroupMember.id)).where(GroupMember.group_id == group_id)
        )
        member_count = member_count_result.scalar() or 0

        # 取得管理員數
        admin_count_result = await self.session.execute(
            select(func.count(GroupAdmin.id)).where(GroupAdmin.group_id == group_id)
        )
        admin_count = admin_count_result.scalar() or 0

        return {
            "group": group,
            "member_count": member_count,
            "admin_count": admin_count,
        }

    async def suspend_group(self, group_id: UUID) -> Optional[Group]:
        """停用群組"""
        group = await self.get_by_id(group_id)
        if not group:
            return None

        group.status = "suspended"
        await self.session.flush()
        return group

    async def activate_group(self, group_id: UUID) -> Optional[Group]:
        """重新啟用群組"""
        group = await self.get_by_id(group_id)
        if not group:
            return None

        group.status = "active"
        await self.session.flush()
        return group

    async def delete_group(self, group_id: UUID) -> bool:
        """刪除群組（硬刪除）"""
        group = await self.get_by_id(group_id)
        if not group:
            return False

        await self.session.delete(group)
        await self.session.flush()
        return True

    async def update_group_info(
        self,
        group_id: UUID,
        name: Optional[str] = None,
        description: Optional[str] = None,
        group_code: Optional[str] = None,
    ) -> Optional[Group]:
        """更新群組資訊"""
        group = await self.get_by_id(group_id)
        if not group:
            return None

        if name is not None:
            group.name = name
        if description is not None:
            group.description = description
        if group_code is not None:
            group.group_code = group_code

        await self.session.flush()
        return group


class GroupApplicationRepository(BaseRepository[GroupApplication]):
    """群組申請 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(GroupApplication, session)

    async def get_pending_applications(self) -> List[GroupApplication]:
        """取得待審核的申請"""
        result = await self.session.execute(
            select(GroupApplication)
            .where(GroupApplication.status == "pending")
            .order_by(GroupApplication.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_all_applications(self) -> List[GroupApplication]:
        """取得所有申請"""
        result = await self.session.execute(
            select(GroupApplication).order_by(GroupApplication.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_pending_by_line_group_id(
        self, line_group_id: str
    ) -> Optional[GroupApplication]:
        """根據 LINE Group ID 取得待審核的申請"""
        result = await self.session.execute(
            select(GroupApplication).where(
                GroupApplication.line_group_id == line_group_id,
                GroupApplication.status == "pending",
            )
        )
        return result.scalar_one_or_none()

    async def get_by_line_group_id(
        self, line_group_id: str
    ) -> List[GroupApplication]:
        """根據 LINE Group ID 取得所有申請"""
        result = await self.session.execute(
            select(GroupApplication)
            .where(GroupApplication.line_group_id == line_group_id)
            .order_by(GroupApplication.created_at.desc())
        )
        return list(result.scalars().all())

    async def get_latest_by_line_group_id(
        self, line_group_id: str
    ) -> Optional[GroupApplication]:
        """根據 LINE Group ID 取得最新的有效申請（排除 archived）"""
        result = await self.session.execute(
            select(GroupApplication)
            .where(
                GroupApplication.line_group_id == line_group_id,
                GroupApplication.status != "archived",
            )
            .order_by(GroupApplication.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def get_approved_by_line_group_id(
        self, line_group_id: str
    ) -> Optional[GroupApplication]:
        """根據 LINE Group ID 取得已核准的申請"""
        result = await self.session.execute(
            select(GroupApplication).where(
                GroupApplication.line_group_id == line_group_id,
                GroupApplication.status == "approved",
            )
        )
        return result.scalar_one_or_none()

    async def get_approved_by_password(
        self, password: str
    ) -> List[GroupApplication]:
        """根據群組代碼取得所有已核准的申請"""
        result = await self.session.execute(
            select(GroupApplication).where(
                GroupApplication.group_code == password,
                GroupApplication.status == "approved",
            )
        )
        return list(result.scalars().all())

    async def get_by_group_code(
        self, group_code: str
    ) -> List[GroupApplication]:
        """根據群組代碼取得所有申請"""
        result = await self.session.execute(
            select(GroupApplication)
            .where(GroupApplication.group_code == group_code)
            .order_by(GroupApplication.created_at.desc())
        )
        return list(result.scalars().all())


class GroupMemberRepository(BaseRepository[GroupMember]):
    """群組成員 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(GroupMember, session)

    async def is_member_of_any_active_group(self, user_id: UUID) -> bool:
        """檢查用戶是否為任一已啟用群組的成員"""
        result = await self.session.execute(
            select(GroupMember)
            .join(Group, GroupMember.group_id == Group.id)
            .where(
                GroupMember.user_id == user_id,
                Group.status == "active",
            )
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    async def add_member(self, group_id: UUID, user_id: UUID) -> tuple[GroupMember, bool]:
        """新增群組成員

        Returns:
            (member, is_new): 成員物件和是否為新成員
        """
        # 檢查是否已存在
        result = await self.session.execute(
            select(GroupMember).where(
                GroupMember.group_id == group_id, GroupMember.user_id == user_id
            )
        )
        member = result.scalar_one_or_none()
        is_new = member is None
        if is_new:
            member = GroupMember(group_id=group_id, user_id=user_id)
            member = await self.create(member)
        return member, is_new

    async def get_group_members(self, group_id: UUID) -> List[GroupMember]:
        """取得群組所有成員"""
        result = await self.session.execute(
            select(GroupMember)
            .where(GroupMember.group_id == group_id)
            .options(selectinload(GroupMember.user))
        )
        return list(result.scalars().all())


class GroupAdminRepository(BaseRepository[GroupAdmin]):
    """群組管理員 Repository"""

    def __init__(self, session: AsyncSession):
        super().__init__(GroupAdmin, session)

    async def is_admin(self, group_id: UUID, user_id: UUID) -> bool:
        """檢查使用者是否為群組管理員"""
        result = await self.session.execute(
            select(GroupAdmin).where(
                GroupAdmin.group_id == group_id, GroupAdmin.user_id == user_id
            )
        )
        return result.scalar_one_or_none() is not None

    async def add_admin(
        self, group_id: UUID, user_id: UUID, granted_by: Optional[UUID] = None
    ) -> GroupAdmin:
        """新增群組管理員"""
        admin = GroupAdmin(group_id=group_id, user_id=user_id, granted_by=granted_by)
        return await self.create(admin)

    async def remove_admin(self, group_id: UUID, user_id: UUID) -> bool:
        """移除群組管理員，回傳是否成功"""
        result = await self.session.execute(
            select(GroupAdmin).where(
                GroupAdmin.group_id == group_id, GroupAdmin.user_id == user_id
            )
        )
        admin = result.scalar_one_or_none()
        if admin:
            await self.session.delete(admin)
            await self.session.flush()
            return True
        return False

    async def get_user_admin_groups(self, user_id: UUID) -> List[GroupAdmin]:
        """取得使用者管理的群組"""
        result = await self.session.execute(
            select(GroupAdmin)
            .where(GroupAdmin.user_id == user_id)
            .options(selectinload(GroupAdmin.group))
        )
        return list(result.scalars().all())

    async def get_group_admins(self, group_id: UUID) -> List[GroupAdmin]:
        """取得群組所有管理員"""
        result = await self.session.execute(
            select(GroupAdmin)
            .where(GroupAdmin.group_id == group_id)
            .options(selectinload(GroupAdmin.user))
        )
        return list(result.scalars().all())
