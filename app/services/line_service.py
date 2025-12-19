"""LINE 服務 - 整合 jaba-line-bot 與 jaba 功能"""
import hashlib
import hmac
import base64
import logging
import os
from datetime import date
from decimal import Decimal
from typing import Optional
from uuid import UUID

from linebot.v3 import WebhookParser
from linebot.v3.messaging import (
    ApiClient,
    Configuration,
    MessagingApi,
    ReplyMessageRequest,
    TextMessage,
    PushMessageRequest,
    QuickReply,
    QuickReplyItem,
    PostbackAction,
)
from linebot.v3.webhooks import MessageEvent, TextMessageContent
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from app.config import settings
from app.models.user import User
from app.models.group import Group, GroupApplication
from app.models.chat import ChatMessage
from app.models.order import OrderSession, Order, OrderItem, GroupTodayStore
from app.models.store import Store
from app.models.menu import Menu, MenuCategory, MenuItem
from app.repositories import (
    UserRepository,
    GroupRepository,
    GroupMemberRepository,
    GroupAdminRepository,
    GroupApplicationRepository,
    ChatRepository,
    GroupTodayStoreRepository,
    OrderSessionRepository,
    OrderRepository,
    OrderItemRepository,
    StoreRepository,
    MenuItemRepository,
)
from app.services.ai_service import AiService, sanitize_user_input
from app.services.cache_service import CacheService
from app.repositories import AiPromptRepository, SecurityLogRepository
from app.models.system import SecurityLog

logger = logging.getLogger("jaba.line")

# 申請連結（可從環境變數讀取完整 URL，預設為相對路徑）
APPLY_URL = os.environ.get("APP_URL", "") + "/board.html"


class LineService:
    """LINE 服務"""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.channel_secret = settings.line_channel_secret
        self.channel_access_token = settings.line_channel_access_token

        # 設定 API 客戶端
        configuration = Configuration(access_token=self.channel_access_token)
        self.api_client = ApiClient(configuration)
        self.messaging_api = MessagingApi(self.api_client)

        # Webhook 解析器
        self.parser = WebhookParser(self.channel_secret)

        # Repositories
        self.user_repo = UserRepository(session)
        self.group_repo = GroupRepository(session)
        self.member_repo = GroupMemberRepository(session)
        self.admin_repo = GroupAdminRepository(session)
        self.application_repo = GroupApplicationRepository(session)
        self.chat_repo = ChatRepository(session)
        self.today_store_repo = GroupTodayStoreRepository(session)
        self.session_repo = OrderSessionRepository(session)
        self.order_repo = OrderRepository(session)
        self.order_item_repo = OrderItemRepository(session)
        self.store_repo = StoreRepository(session)
        self.menu_item_repo = MenuItemRepository(session)
        self.prompt_repo = AiPromptRepository(session)
        self.security_log_repo = SecurityLogRepository(session)

        # AI 服務
        self.ai_service = AiService()

    def verify_signature(self, body: str, signature: str) -> bool:
        """驗證 LINE 簽章"""
        hash = hmac.new(
            self.channel_secret.encode("utf-8"),
            body.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        expected_signature = base64.b64encode(hash).decode("utf-8")
        return hmac.compare_digest(signature, expected_signature)

    async def _get_group_code(self, group: Group) -> Optional[str]:
        """取得群組的 group_code（從 GroupApplication）"""
        result = await self.session.execute(
            select(GroupApplication)
            .where(
                GroupApplication.line_group_id == group.line_group_id,
                GroupApplication.status == "approved",
            )
            .order_by(GroupApplication.created_at.desc())
        )
        app = result.scalar_one_or_none()
        return app.group_code if app else None

    async def _get_stores_for_group(self, group: Group) -> list[Store]:
        """取得群組可用的店家（全局 + 群組專屬）"""
        group_code = await self._get_group_code(group)
        if group_code:
            return await self.store_repo.get_stores_for_group_code(group_code)
        # 如果沒有 group_code，只返回全局店家
        return await self.store_repo.get_stores_by_scope("global")

    def parse_webhook(self, body: str, signature: str):
        """解析 Webhook 事件"""
        return self.parser.parse(body, signature)

    async def reply_message(self, reply_token: str, message: str) -> None:
        """回覆訊息"""
        try:
            logger.info(f"Replying message: {message[:50]}...")
            self.messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[TextMessage(text=message)],
                )
            )
            logger.info("Reply sent successfully")
        except Exception as e:
            logger.error(f"Reply message error: {e}", exc_info=True)

    async def _reply_with_quick_reply(
        self, reply_token: str, message: str, items: list
    ) -> None:
        """回覆帶有 Quick Reply 按鈕的訊息"""
        try:
            logger.info(f"Replying with quick reply: {message[:50]}...")
            self.messaging_api.reply_message(
                ReplyMessageRequest(
                    reply_token=reply_token,
                    messages=[
                        TextMessage(
                            text=message,
                            quick_reply=QuickReply(items=items),
                        )
                    ],
                )
            )
            logger.info("Quick reply sent successfully")
        except Exception as e:
            logger.error(f"Quick reply error: {e}", exc_info=True)

    async def push_message(self, to: str, message: str) -> None:
        """推送訊息"""
        try:
            self.messaging_api.push_message(
                PushMessageRequest(
                    to=to,
                    messages=[TextMessage(text=message)],
                )
            )
        except Exception as e:
            logger.error(f"Push message error: {e}")

    async def get_user_profile(self, user_id: str) -> Optional[dict]:
        """取得使用者資料"""
        try:
            profile = self.messaging_api.get_profile(user_id)
            return {
                "user_id": profile.user_id,
                "display_name": profile.display_name,
                "picture_url": profile.picture_url,
            }
        except Exception as e:
            logger.error(f"Get user profile error: {e}")
            return None

    async def get_group_member_profile(
        self, group_id: str, user_id: str
    ) -> Optional[dict]:
        """取得群組成員資料"""
        try:
            profile = self.messaging_api.get_group_member_profile(group_id, user_id)
            return {
                "user_id": profile.user_id,
                "display_name": profile.display_name,
                "picture_url": profile.picture_url,
            }
        except Exception as e:
            logger.error(f"Get group member profile error: {e}")
            return None

    async def get_group_name(self, group_id: str) -> str:
        """取得群組名稱"""
        try:
            summary = self.messaging_api.get_group_summary(group_id)
            return summary.group_name
        except Exception as e:
            logger.error(f"Get group name error: {e}")
            return ""

    # ========== 訊息處理主流程 ==========

    async def handle_message(
        self,
        user_id: str,
        group_id: Optional[str],
        text: str,
        reply_token: str,
    ) -> None:
        """處理訊息 - 主入口"""
        # 取得或建立使用者
        user = await self.user_repo.get_or_create(user_id)

        # 檢查使用者是否被封鎖（靜默忽略）
        if user.is_banned:
            logger.debug(f"Ignoring message from banned user: {user_id}")
            return

        # 嘗試取得顯示名稱
        if not user.display_name:
            if group_id:
                profile = await self.get_group_member_profile(group_id, user_id)
            else:
                profile = await self.get_user_profile(user_id)
            if profile:
                user.display_name = profile["display_name"]
                await self.user_repo.update(user)

        # 區分個人/群組訊息
        if group_id:
            await self._handle_group_message(user, group_id, text, reply_token)
        else:
            await self._handle_personal_message(user, text, reply_token)

    async def _handle_personal_message(
        self,
        user: User,
        text: str,
        reply_token: str,
    ) -> None:
        """處理個人訊息 - 永遠回應"""
        text_stripped = text.strip()

        # 特殊指令處理
        special_response = await self._handle_special_command(
            user, text_stripped, None, is_personal=True
        )
        if special_response:
            await self.reply_message(reply_token, special_response)
            return

        # 檢查是否為任一已啟用群組的成員
        is_member = await self.member_repo.is_member_of_any_active_group(user.id)
        if not is_member:
            await self.reply_message(
                reply_token,
                self._guide_to_apply(is_group=False),
            )
            return

        # 個人模式快捷指令處理
        quick_response = await self._handle_personal_quick_command(user, text_stripped)
        if quick_response:
            await self.reply_message(reply_token, quick_response)
            return

        # 記錄訊息
        chat_msg = ChatMessage(user_id=user.id, role="user", content=text)
        await self.chat_repo.create(chat_msg)

        # 呼叫 AI（個人模式）
        try:
            # 輸入過濾
            sanitized_text, trigger_reasons = sanitize_user_input(text)
            if trigger_reasons:
                await self._log_security_event(
                    line_user_id=user.line_user_id,
                    display_name=user.display_name,
                    line_group_id=None,
                    original_message=text,
                    sanitized_message=sanitized_text,
                    trigger_reasons=trigger_reasons,
                    context_type="personal",
                )
                # 有可疑內容，靜默不回應
                return

            system_prompt = await self._get_personal_system_prompt()

            # 取得個人對話歷史
            history_limit = settings.chat_history_limit
            history = await self.chat_repo.get_user_messages(
                user.id,
                limit=history_limit,
            )

            ai_response = await self.ai_service.chat(
                message=sanitized_text,
                system_prompt=system_prompt,
                context={
                    "mode": "personal_preferences",
                    "user_name": user.display_name or "使用者",
                    "user_preferences": user.preferences,
                },
                history=[
                    {
                        "role": msg.role,
                        "name": user.display_name if msg.role == "user" else "助手",
                        "content": msg.content,
                    }
                    for msg in history[-history_limit:]
                ],
            )

            response_text = ai_response.get("message", "抱歉，我無法理解。")

            # 處理 AI 動作
            actions = ai_response.get("actions", [])
            if actions:
                extra_messages = await self._execute_personal_actions(user, actions)
                # 將額外訊息附加到回應
                if extra_messages:
                    response_text = response_text + "\n\n" + "\n\n".join(extra_messages)

            # 記錄 AI 回應
            ai_msg = ChatMessage(user_id=user.id, role="assistant", content=response_text)
            await self.chat_repo.create(ai_msg)

            await self.reply_message(reply_token, response_text)

        except Exception as e:
            logger.error(f"Personal chat error: {e}", exc_info=True)
            await self.reply_message(reply_token, "抱歉，我現在有點忙，請稍後再試。")

    async def _handle_group_message(
        self,
        user: User,
        line_group_id: str,
        text: str,
        reply_token: str,
    ) -> None:
        """處理群組訊息 - 根據點餐狀態過濾"""
        text_stripped = text.strip()

        # 取得或建立群組
        group = await self.group_repo.get_or_create(line_group_id)

        # 如果群組名稱為空，嘗試從 LINE API 取得
        if not group.name:
            group_name = await self.get_group_name(line_group_id)
            if group_name:
                group.name = group_name
                await self.group_repo.update(group)

        # 特殊指令處理（管理員綁定、ID 查詢、幫助）
        special_response = await self._handle_special_command(
            user, text_stripped, group, is_personal=False
        )
        if special_response:
            await self.reply_message(reply_token, special_response)
            return

        # 檢查群組是否已啟用
        if group.status == "suspended":
            # 被凍結的群組，只回應 help 請求
            text_lower = text.strip().lower()
            if text_lower in ["help", "jaba", "呷爸", "@jaba", "@呷爸"]:
                await self.reply_message(
                    reply_token,
                    "⚠️ 此群組已被管理員凍結\n\n"
                    "點餐功能暫時無法使用。\n"
                    "如有疑問，請聯繫系統管理員。",
                )
            return

        if group.status != "active":
            # 群組未啟用（pending/inactive/rejected），使用 AI 引導申請
            await self._handle_pending_group_chat(user, group, text, reply_token)
            return

        # 新增成員記錄
        _, is_new_member = await self.member_repo.add_member(group.id, user.id)
        if is_new_member:
            from app.broadcast import emit_group_update
            await emit_group_update({"action": "member_added", "group_id": str(group.id)})

        # 檢查是否在點餐中
        active_session = await self.session_repo.get_active_session(group.id)
        is_ordering = active_session is not None

        # 快捷指令處理（開單、收單、菜單等）- 所有人都可用
        quick_response = await self._handle_quick_command(
            user, group, text_stripped, active_session
        )
        if quick_response:
            await self.reply_message(reply_token, quick_response)
            return

        # 管理員指令處理（僅在非點餐中時）
        if not is_ordering:
            admin_response = await self._handle_admin_command(user, group, text_stripped)
            if admin_response:
                await self.reply_message(reply_token, admin_response)
                return

        # 根據點餐狀態決定是否回應
        should_reply, cleaned_message = self._should_respond_in_group(
            text_stripped, is_ordering
        )

        if not should_reply:
            return

        # 呼叫 AI 處理
        await self._handle_ai_chat(user, group, active_session, text, reply_token)

    def _should_respond_in_group(
        self, text: str, is_ordering: bool
    ) -> tuple[bool, str]:
        """判斷群組中是否應該回應

        Returns:
            (should_respond, cleaned_message)
        """
        text_lower = text.lower()

        if is_ordering:
            # 點餐中：所有訊息都回應
            return True, text

        # 非點餐中：只回應特定指令
        if text in ["開單", "菜單"]:
            return True, text

        # 呼叫幫助（@呷爸、呷爸）
        trigger_keywords = ["jaba", "呷爸", "點餐"]
        for keyword in trigger_keywords:
            if text_lower in [keyword.lower(), f"@{keyword.lower()}"]:
                return True, "help"

        return False, text

    # ========== 特殊指令處理 ==========

    async def _handle_special_command(
        self,
        user: User,
        text: str,
        group: Optional[Group],
        is_personal: bool,
    ) -> Optional[str]:
        """處理特殊指令（ID 查詢、幫助）"""
        text_lower = text.lower()

        # 幫助請求 (pending 群組走 AI 引導流程)
        help_keywords = ["help", "jaba", "呷爸", "@jaba", "@呷爸"]
        if text_lower in help_keywords:
            # pending 群組不在這處理，讓它走 _handle_pending_group_chat (AI 引導)
            if group and group.status != "active":
                return None
            return await self._generate_help_message(user, group, is_personal)

        # ID 查詢
        if text_lower in ["id", "群組id", "groupid", "userid"]:
            return self._generate_id_info(user, group, is_personal)

        return None

    def _guide_to_apply(self, is_group: bool = True) -> str:
        """引導用戶申請開通（備用訊息）"""
        if is_group:
            return (
                "📝 此群組尚未開通點餐功能\n\n"
                "【方式一】直接在這裡申請\n"
                "請告訴我以下資訊：\n"
                "1. 群組名稱（如「XX公司午餐團」）\n"
                "2. 聯絡方式（LINE ID 或 Email）\n"
                "3. 群組代碼（自訂，管理員綁定用）\n\n"
                "【方式二】網頁申請\n"
                f"前往 {APPLY_URL}\n"
                "輸入「id」可取得群組 ID\n\n"
                "審核通過後即可開始使用！"
            )
        else:
            return (
                "👋 哩賀！哇係呷爸點餐助手\n\n"
                "個人聊天功能僅限已加入點餐群組的成員使用。\n\n"
                "請先加入一個已開通的 LINE 群組，\n"
                f"或前往 {APPLY_URL} 申請開通您的群組"
            )

    async def _generate_help_message(
        self,
        user: User,
        group: Optional[Group],
        is_personal: bool,
    ) -> str:
        """產生幫助訊息"""
        lines = ["🍱 呷爸 - AI 午餐訂便當助手", ""]

        if is_personal:
            # 個人模式 - 檢查是否為群組成員
            is_member = await self.member_repo.is_member_of_any_active_group(user.id)
            if is_member:
                lines.append("✅ 狀態：已啟用")
                lines.append("")
                lines.append("【偏好設定】")
                lines.append("• 告訴我你的稱呼（如「叫我小明」）")
                lines.append("• 告訴我飲食偏好（如「我不吃辣」）")
                lines.append("")
                lines.append("【查詢指令】")
                lines.append("• 「我的設定」查看偏好設定")
                lines.append("• 「我的群組」查看所屬群組")
                lines.append("• 「歷史訂單」查看訂單紀錄")
                lines.append("• 「清除設定」清除所有偏好")
                lines.append("")
                lines.append("💡 要點餐請到 LINE 群組，說「開單」開始！")
            else:
                lines.append("⚠️ 狀態：未啟用")
                lines.append("")
                lines.append("個人功能僅限已加入點餐群組的成員使用")
                lines.append("")
                lines.append(f"申請開通群組：{APPLY_URL}")
        else:
            # 群組模式
            if group and group.status == "active":
                lines.append("✅ 狀態：已啟用")

                # 檢查是否在點餐中
                active_session = await self.session_repo.get_active_session(group.id)
                if active_session:
                    lines.append("🛒 點餐中")
                else:
                    lines.append("💤 未在點餐中")

                # 顯示今日店家
                today_stores = await self.today_store_repo.get_today_stores(group.id)
                if today_stores:
                    store_names = "、".join([ts.store.name for ts in today_stores])
                    lines.append(f"🏪 今日店家：{store_names}")
                else:
                    lines.append("🏪 今日店家：尚未設定")

                lines.append("")
                if active_session:
                    lines.append("【可用指令】")
                    lines.append("• 直接說出餐點即可點餐")
                    lines.append("• 「+1」或「我也要」跟單")
                    lines.append("• 「收單」或「結單」結束點餐")
                    lines.append("• 「菜單」查看今日菜單")
                    lines.append("• 「目前訂單」查看訂單狀況")
                else:
                    lines.append("【可用指令】")
                    lines.append("• 「開單」開始群組點餐")
                    lines.append("• 「菜單」查看今日菜單")

                # 檢查是否為管理員
                is_admin = await self.admin_repo.is_admin(group.id, user.id)
                if is_admin:
                    lines.append("")
                    lines.append("【管理員指令】")
                    lines.append("• 「今日」查看今日店家")
                    lines.append("• 直接輸入店名 - 設定今日店家")
                    lines.append("• 「加 [店名]」新增店家")
                    lines.append("• 「移除 [店名]」移除店家")
                    lines.append("• 「清除」清除所有")
                    lines.append("• 「解除管理員」解除身份")
                else:
                    lines.append("")
                    lines.append("【綁定管理員】")
                    lines.append("• 輸入「管理員 [群組代碼]」綁定")
            else:
                lines.append("⚠️ 狀態：未開通")
                lines.append("")
                lines.append("此群組尚未開通點餐功能")
                lines.append("")
                lines.append(f"申請開通：{APPLY_URL}")

        return "\n".join(lines)

    def _generate_id_info(
        self,
        user: User,
        group: Optional[Group],
        is_personal: bool,
    ) -> str:
        """產生 ID 資訊"""
        if is_personal:
            return f"📋 ID 資訊\n\n你的用戶 ID:\n{user.line_user_id}"
        else:
            return (
                f"📋 ID 資訊\n\n"
                f"群組 ID:\n{group.line_group_id}\n\n"
                f"你的用戶 ID:\n{user.line_user_id}"
            )

    # ========== 個人模式快捷指令處理 ==========

    async def _handle_personal_quick_command(
        self,
        user: User,
        text: str,
    ) -> Optional[str]:
        """處理個人模式快捷指令（我的設定、我的群組、歷史訂單、清除設定）"""
        # 查詢偏好設定
        if text in ["我的設定", "設定", "偏好", "偏好設定", "我的偏好"]:
            return self._get_preferences_summary(user)

        # 查詢所屬群組
        if text in ["我的群組", "群組", "群組列表", "所屬群組"]:
            return await self._get_user_groups_summary(user)

        # 查詢歷史訂單
        if text in ["歷史訂單", "訂單紀錄", "訂單歷史", "我的訂單", "點過什麼"]:
            return await self._get_order_history_summary(user)

        # 清除偏好設定
        if text in ["清除設定", "刪除設定", "重設設定", "清除偏好"]:
            return await self._clear_user_preferences(user)

        return None

    def _get_preferences_summary(self, user: User) -> str:
        """取得使用者偏好設定摘要"""
        preferences = user.preferences or {}

        if not preferences:
            return (
                "📋 我的設定\n\n"
                "您尚未設定任何偏好。\n\n"
                "💡 您可以告訴我：\n"
                "• 您的稱呼（如「叫我小明」）\n"
                "• 飲食限制（如「我不吃辣」）\n"
                "• 口味偏好（如「我喜歡清淡」）"
            )

        lines = ["📋 我的設定", ""]

        # 稱呼
        if preferences.get("preferred_name"):
            lines.append(f"👤 稱呼：{preferences['preferred_name']}")

        # 飲食限制
        dietary = preferences.get("dietary_restrictions")
        if dietary:
            if isinstance(dietary, list):
                lines.append(f"🚫 飲食限制：{', '.join(dietary)}")
            else:
                lines.append(f"🚫 飲食限制：{dietary}")

        # 口味偏好
        taste = preferences.get("taste_preferences")
        if taste:
            if isinstance(taste, list):
                lines.append(f"😋 口味偏好：{', '.join(taste)}")
            else:
                lines.append(f"😋 口味偏好：{taste}")

        # 其他偏好
        other_keys = [k for k in preferences.keys()
                      if k not in ["preferred_name", "dietary_restrictions", "taste_preferences"]]
        for key in other_keys:
            value = preferences[key]
            if isinstance(value, list):
                lines.append(f"• {key}：{', '.join(str(v) for v in value)}")
            else:
                lines.append(f"• {key}：{value}")

        lines.append("")
        lines.append("💡 要修改設定，直接告訴我即可")
        lines.append("💡 要清除設定，請輸入「清除設定」")

        return "\n".join(lines)

    async def _get_user_groups_summary(self, user: User) -> str:
        """取得使用者所屬群組摘要"""
        from app.models.group import Group, GroupMember

        # 查詢使用者所屬的已啟用群組
        result = await self.session.execute(
            select(Group, GroupMember.joined_at)
            .join(GroupMember, GroupMember.group_id == Group.id)
            .where(GroupMember.user_id == user.id)
            .where(Group.status == "active")
            .order_by(GroupMember.joined_at.desc())
        )
        groups = result.all()

        if not groups:
            return (
                "📋 我的群組\n\n"
                "您尚未加入任何群組。\n\n"
                "💡 加入已開通的 LINE 群組後，\n"
                "在群組中發言即可自動加入。"
            )

        lines = ["📋 我的群組", ""]

        for group, joined_at in groups:
            group_name = group.name or f"群組 {group.line_group_id[:8]}..."
            joined_str = joined_at.strftime("%Y/%m/%d") if joined_at else "未知"
            lines.append(f"• {group_name}")
            lines.append(f"  加入時間：{joined_str}")
            lines.append("")

        lines.append(f"共 {len(groups)} 個群組")

        return "\n".join(lines)

    async def _get_order_history_summary(self, user: User) -> str:
        """取得使用者歷史訂單摘要"""
        from app.models.order import Order, OrderItem, OrderSession
        from app.models.group import Group
        from app.models.store import Store

        # 查詢使用者最近 10 筆訂單
        result = await self.session.execute(
            select(Order)
            .where(Order.user_id == user.id)
            .options(
                selectinload(Order.items),
                selectinload(Order.store),
                selectinload(Order.session).selectinload(OrderSession.group),
            )
            .order_by(Order.created_at.desc())
            .limit(10)
        )
        orders = result.scalars().all()

        if not orders:
            return (
                "📋 歷史訂單\n\n"
                "您尚無訂單紀錄。\n\n"
                "💡 到 LINE 群組說「開單」開始點餐！"
            )

        lines = ["📋 歷史訂單（最近 10 筆）", ""]

        for order in orders:
            # 日期
            order_date = order.created_at.strftime("%Y/%m/%d %H:%M")

            # 群組名稱
            group_name = "未知群組"
            if order.session and order.session.group:
                group_name = order.session.group.name or "未命名群組"

            # 店家名稱
            store_name = order.store.name if order.store else "未知店家"

            lines.append(f"📅 {order_date}")
            lines.append(f"   群組：{group_name}")
            lines.append(f"   店家：{store_name}")

            # 品項
            for item in order.items:
                item_text = f"   • {item.name}"
                if item.quantity > 1:
                    item_text += f" x{item.quantity}"
                item_text += f" ${int(item.subtotal)}"
                lines.append(item_text)

            lines.append(f"   💰 小計：${int(order.total_amount)}")
            lines.append("")

        return "\n".join(lines)

    async def _clear_user_preferences(self, user: User) -> str:
        """清除使用者偏好設定"""
        user.preferences = {}
        await self.user_repo.update(user)

        return (
            "✅ 已清除您的偏好設定\n\n"
            "您可以隨時重新設定：\n"
            "• 告訴我您的稱呼\n"
            "• 告訴我飲食限制\n"
            "• 告訴我口味偏好"
        )

    # ========== 群組管理員指令處理 ==========

    async def _handle_admin_command(
        self,
        user: User,
        group: Group,
        text: str,
    ) -> Optional[str]:
        """處理群組管理員指令（綁定管理員、今日店家管理）

        - 「管理員 [代碼]」：任何人都可以嘗試綁定
        - 其他指令：僅限群組管理員可執行，非管理員靜默忽略
        """
        # 管理員綁定指令（不需要先是管理員）
        if text.startswith("管理員"):
            group_code = text[3:].strip()  # 移除「管理員」
            if not group_code:
                return "⚠️ 請輸入群組代碼\n例如：管理員 1234"
            return await self._bind_admin(user, group, group_code)

        # 解除管理員指令（需要是管理員）
        if text == "解除管理員":
            return await self._unbind_admin(user, group)

        # 檢查是否為其他管理員指令
        admin_commands = [
            "今日",
            "清除",
        ]
        admin_prefixes = [
            "加",
            "移除",
        ]

        is_admin_cmd = text in admin_commands or any(
            text.startswith(prefix) for prefix in admin_prefixes
        )

        # 檢查使用者是否為群組管理員
        is_admin = await self.admin_repo.is_admin(group.id, user.id)

        # 非已知指令時，嘗試用關鍵字匹配店家（僅限管理員）
        if not is_admin_cmd:
            if is_admin:
                result = await self._try_set_store_by_keyword(group, user, text)
                if result:
                    return result
                # 管理員輸入但沒匹配到任何東西，顯示幫助
                return self._get_admin_help()
            return None

        # 以下為已知管理員指令，需要管理員權限
        if not is_admin:
            # 非管理員靜默忽略
            return None

        # 查詢今日店家
        if text == "今日":
            return await self._get_today_stores_summary(group)

        # 清除今日店家
        if text == "清除":
            return await self._clear_today_stores(group, user)

        # 加 XXX（新增一家）
        if text.startswith("加"):
            store_name = text[1:].strip()  # 移除「加」
            if not store_name:
                return "⚠️ 請輸入店家名稱\n例如：加 好吃便當"
            return await self._add_today_store(group, user, store_name)

        # 移除 XXX
        if text.startswith("移除"):
            store_name = text[2:].strip()  # 移除「移除」
            if not store_name:
                return "⚠️ 請輸入店家名稱\n例如：移除 好吃便當"
            return await self._remove_today_store(group, user, store_name)

        return None

    async def _try_set_store_by_keyword(
        self, group: Group, user: User, keyword: str
    ) -> Optional[str]:
        """嘗試用關鍵字匹配店家並設定為今日店家"""
        from app.broadcast import emit_store_change, flush_events

        # 模糊匹配店名
        result = await self.session.execute(
            select(Store).where(Store.name.contains(keyword))
        )
        matched_stores = result.scalars().all()

        if not matched_stores:
            # 沒有匹配，不處理
            return None

        if len(matched_stores) == 1:
            # 只有一間，直接設定
            store = matched_stores[0]
            await self.today_store_repo.clear_today_stores(group.id)
            await self.today_store_repo.set_today_store(group.id, store.id, user.id)
            CacheService.clear_today_stores(str(group.id))
            # 先提交交易，確保其他連線可以讀到新資料
            await self.session.commit()
            # 廣播店家變更
            await emit_store_change(str(group.id), {
                "group_id": str(group.id),
                "action": "set",
                "store_name": store.name,
            })
            await flush_events()
            return f"✅ 已設定今日店家：{store.name}"

        # 多間匹配，列出選項
        lines = [f"🔍 找到 {len(matched_stores)} 間符合「{keyword}」的店家：", ""]
        for store in matched_stores:
            lines.append(f"• {store.name}")
        lines.append("")
        lines.append("請輸入完整店名")

        return "\n".join(lines)

    def _get_admin_help(self) -> str:
        """取得管理員指令幫助"""
        return (
            "📋 管理員指令說明\n\n"
            "【查看/設定今日店家】\n"
            "• 「今日」查看目前設定\n"
            "• 直接輸入店名即可設定\n\n"
            "【其他操作】\n"
            "• 「加 [店名]」新增店家\n"
            "• 「移除 [店名]」移除店家\n"
            "• 「清除」清除所有\n"
            "• 「解除管理員」解除身份\n\n"
            "💡 輸入「今日」可查看可用店家列表"
        )

    async def _bind_admin(
        self, user: User, group: Group, password: str
    ) -> str:
        """綁定管理員身份"""
        # 檢查是否已是管理員
        is_admin = await self.admin_repo.is_admin(group.id, user.id)
        if is_admin:
            return "✅ 您已經是管理員了"

        # 驗證群組代碼（直接從 Group 取得，不需查 Application）
        if not group.group_code or group.group_code != password:
            return "⚠️ 代碼錯誤"

        # 綁定成功：將用戶加入管理員
        await self.admin_repo.add_admin(group.id, user.id)

        return (
            "✅ 已綁定為群組管理員！\n\n"
            "現在可以使用以下指令：\n"
            "• 今日 - 查看今日店家\n"
            "• 直接輸入店名 - 設定今日店家\n"
            "• 加 [店名] - 新增店家\n"
            "• 移除 [店名] - 移除店家\n"
            "• 清除 - 清除所有\n"
            "• 解除管理員 - 解除管理員身份"
        )

    async def _unbind_admin(self, user: User, group: Group) -> str:
        """解除管理員身份"""
        # 檢查是否是管理員
        is_admin = await self.admin_repo.is_admin(group.id, user.id)
        if not is_admin:
            return "⚠️ 您不是管理員"

        # 檢查是否為最後一個管理員
        admins = await self.admin_repo.get_group_admins(group.id)
        if len(admins) <= 1:
            return "⚠️ 您是此群組唯一的管理員，無法解除\n\n請先讓其他人綁定管理員後再解除"

        # 解除管理員
        await self.admin_repo.remove_admin(group.id, user.id)

        return "✅ 已解除管理員身份\n\n如需重新綁定，請輸入「管理員 [代碼]」"

    async def _get_today_stores_summary(self, group: Group) -> str:
        """查詢今日店家"""
        today_stores = await self.today_store_repo.get_today_stores(group.id)

        # 取得群組可用店家（全局 + 群組專屬）
        all_stores = await self._get_stores_for_group(group)
        available_stores = [s.name for s in all_stores]

        if not today_stores:
            lines = ["📋 今日店家", "", "尚未設定今日店家。"]

            if available_stores:
                lines.append("")
                lines.append("🏪 可用店家（直接輸入店名即可設定）：")
                for name in available_stores:
                    lines.append(f"• {name}")

            return "\n".join(lines)

        lines = ["📋 今日店家", ""]
        for ts in today_stores:
            if ts.store:
                lines.append(f"• {ts.store.name}")

        # 顯示尚未選擇的店家
        today_store_ids = {ts.store_id for ts in today_stores}
        other_stores = [s.name for s in all_stores if s.id not in today_store_ids]
        if other_stores:
            lines.append("")
            lines.append("🏪 其他可用店家：")
            for name in other_stores:
                lines.append(f"• {name}")

        lines.append("")
        lines.append("💡 直接輸入店名可替換，或：")
        lines.append("• 加 [店名] - 新增店家")
        lines.append("• 移除 [店名] - 移除店家")
        lines.append("• 清除 - 清除所有")

        return "\n".join(lines)

    async def _find_store_by_name(
        self, store_name: str, group: Optional[Group] = None
    ) -> Optional[Store]:
        """根據名稱模糊匹配店家（限群組可用範圍）"""
        # 取得群組可用店家
        if group:
            available_stores = await self._get_stores_for_group(group)
        else:
            # 沒有群組時，只搜尋全局店家
            available_stores = await self.store_repo.get_stores_by_scope("global")

        # 先嘗試精確匹配
        for store in available_stores:
            if store.name == store_name:
                return store

        # 模糊匹配（名稱包含輸入）
        matched = [s for s in available_stores if store_name in s.name]

        if len(matched) == 1:
            return matched[0]
        elif len(matched) > 1:
            # 多個匹配，回傳第一個（通常不會發生）
            return matched[0]

        return None

    async def _get_available_stores_hint(self, group: Optional[Group] = None) -> str:
        """取得可用店家列表提示"""
        if group:
            stores = await self._get_stores_for_group(group)
        else:
            # 沒有群組時，只顯示全局店家
            stores = await self.store_repo.get_stores_by_scope("global")

        # 限制顯示 10 個
        stores = stores[:10]

        if not stores:
            return "目前系統中沒有可用的店家。"

        store_names = [s.name for s in stores]
        return "可用店家：" + "、".join(store_names)

    async def _set_today_store(
        self, group: Group, user: User, store_name: str
    ) -> str:
        """設定今日店家（清除其他並設定）"""
        from app.broadcast import emit_store_change, flush_events

        # 查找店家
        store = await self._find_store_by_name(store_name, group)
        if not store:
            hint = await self._get_available_stores_hint(group)
            return f"⚠️ 找不到店家「{store_name}」\n\n{hint}"

        # 清除原有今日店家
        await self.today_store_repo.clear_today_stores(group.id)

        # 設定新店家
        await self.today_store_repo.set_today_store(group.id, store.id, user.id)

        # 清除快取
        CacheService.clear_today_stores(str(group.id))

        # 先提交交易，確保其他連線可以讀到新資料
        await self.session.commit()

        # 廣播店家變更
        await emit_store_change(str(group.id), {
            "group_id": str(group.id),
            "action": "set",
            "store_name": store.name,
        })
        await flush_events()

        return f"✅ 已設定今日店家：{store.name}"

    async def _add_today_store(
        self, group: Group, user: User, store_name: str
    ) -> str:
        """新增今日店家（不清除原有）"""
        from app.broadcast import emit_store_change, flush_events

        # 查找店家
        store = await self._find_store_by_name(store_name, group)
        if not store:
            hint = await self._get_available_stores_hint(group)
            return f"⚠️ 找不到店家「{store_name}」\n\n{hint}"

        # 檢查是否已經是今日店家
        today_stores = await self.today_store_repo.get_today_stores(group.id)
        for ts in today_stores:
            if ts.store_id == store.id:
                return f"⚠️ {store.name} 已經是今日店家了"

        # 新增店家
        await self.today_store_repo.set_today_store(group.id, store.id, user.id)

        # 清除快取
        CacheService.clear_today_stores(str(group.id))

        # 先提交交易，確保其他連線可以讀到新資料
        await self.session.commit()

        # 廣播店家變更
        await emit_store_change(str(group.id), {
            "group_id": str(group.id),
            "action": "add",
            "store_name": store.name,
        })
        await flush_events()

        return f"✅ 已新增今日店家：{store.name}"

    async def _remove_today_store(
        self, group: Group, user: User, store_name: str
    ) -> str:
        """移除特定今日店家"""
        from app.broadcast import emit_store_change, flush_events

        # 取得今日店家
        today_stores = await self.today_store_repo.get_today_stores(group.id)

        if not today_stores:
            return "⚠️ 目前沒有設定今日店家"

        # 在今日店家中匹配店名
        matched_store = None
        for ts in today_stores:
            if ts.store and (
                ts.store.name == store_name or store_name in ts.store.name
            ):
                matched_store = ts.store
                break

        if not matched_store:
            current_stores = [ts.store.name for ts in today_stores if ts.store]
            return (
                f"⚠️ 今日店家中找不到「{store_name}」\n\n"
                f"目前今日店家：{'、'.join(current_stores)}"
            )

        # 移除店家
        await self.today_store_repo.remove_today_store(group.id, matched_store.id)

        # 清除快取
        CacheService.clear_today_stores(str(group.id))

        # 先提交交易，確保其他連線可以讀到新資料
        await self.session.commit()

        # 廣播店家變更
        await emit_store_change(str(group.id), {
            "group_id": str(group.id),
            "action": "remove",
            "store_name": matched_store.name,
        })
        await flush_events()

        return f"✅ 已移除今日店家：{matched_store.name}"

    async def _clear_today_stores(self, group: Group, user: User) -> str:
        """清除所有今日店家"""
        from app.broadcast import emit_store_change, flush_events

        # 檢查是否有今日店家
        today_stores = await self.today_store_repo.get_today_stores(group.id)

        if not today_stores:
            return "⚠️ 目前沒有設定今日店家"

        # 清除所有
        await self.today_store_repo.clear_today_stores(group.id)

        # 清除快取
        CacheService.clear_today_stores(str(group.id))

        # 先提交交易，確保其他連線可以讀到新資料
        await self.session.commit()

        # 廣播店家變更
        await emit_store_change(str(group.id), {
            "group_id": str(group.id),
            "action": "clear",
        })
        await flush_events()

        return "✅ 已清除所有今日店家"

    # ========== 群組快捷指令處理 ==========

    async def _handle_quick_command(
        self,
        user: User,
        group: Group,
        text: str,
        active_session: Optional[OrderSession],
    ) -> Optional[str]:
        """處理快捷指令（開單、收單、菜單等）"""
        text_lower = text.lower()

        # 開單
        if text == "開單":
            return await self._start_ordering(user, group, active_session)

        # 收單/結單
        if text_lower in ["收單", "結單"]:
            return await self._end_ordering(user, group, active_session)

        # 菜單
        if text == "菜單":
            return await self._get_menu_summary(group)

        # 目前訂單
        if text_lower in ["目前訂單", "訂單", "查看訂單", "訂單狀況", "點了什麼"]:
            if active_session:
                return await self._get_session_summary_by_id(active_session.id)
            return None

        return None

    async def _start_ordering(
        self,
        user: User,
        group: Group,
        active_session: Optional[OrderSession],
    ) -> str:
        """開始群組點餐"""
        from app.broadcast import emit_session_status, flush_events

        if active_session:
            return "⚠️ 此群組已經在點餐中了！\n\n直接說出你要點的餐點即可。"

        # 檢查是否有設定今日店家
        today_stores = await self.today_store_repo.get_today_stores(group.id)
        if not today_stores:
            return "⚠️ 尚未設定今日店家，無法開單\n\n請管理員先設定今日店家"

        # 開始新 session
        new_session = await self.session_repo.start_session(group.id, user.id)

        # 記錄系統訊息標記新 session 開始（讓 AI 知道這是新的點餐）
        store_names = "、".join([ts.store.name for ts in today_stores])
        await self.chat_repo.add_message(
            role="system",
            content=f"=== 新的點餐開始 ===\n今日店家：{store_names}\n由 {user.display_name} 發起",
            group_id=group.id,
            session_id=new_session.id,
        )

        # 先 commit 再廣播，確保其他連線能讀到更新
        await self.session.commit()

        # 廣播 Session 狀態
        await emit_session_status(str(group.id), {
            "group_id": str(group.id),
            "session_id": str(new_session.id),
            "status": "ordering",
            "started_by": user.display_name,
        })
        await flush_events()

        # 取得今日菜單摘要
        menu_text = await self._get_menu_summary(group)

        return f"🍱 開始群組點餐！\n\n{menu_text}\n\n直接說出餐點即可，說「收單」或「結單」結束點餐。"

    async def _end_ordering(
        self,
        user: User,
        group: Group,
        active_session: Optional[OrderSession],
    ) -> str:
        """結束群組點餐"""
        from app.broadcast import emit_session_status, flush_events

        if not active_session:
            return "⚠️ 目前沒有進行中的點餐。\n\n說「開單」開始群組點餐。"

        # 結束 session
        await self.session_repo.end_session(active_session, user.id)

        # 產生訂單摘要
        summary = await self._get_session_summary_by_id(active_session.id)

        # 先 commit 再廣播，確保其他連線能讀到更新
        await self.session.commit()

        # 廣播 Session 狀態
        await emit_session_status(str(group.id), {
            "group_id": str(group.id),
            "session_id": str(active_session.id),
            "status": "ended",
            "ended_by": user.display_name,
            "summary": summary,
        })
        await flush_events()

        return f"✅ 點餐結束！\n\n{summary}"

    async def _get_menu_summary(self, group: Group) -> str:
        """取得今日菜單摘要"""
        today_stores = await self.today_store_repo.get_today_stores(group.id)

        if not today_stores:
            return "📋 今日尚未設定店家菜單"

        lines = ["📋 今日菜單"]

        for ts in today_stores:
            store = ts.store
            if not store:
                continue

            lines.append(f"\n【{store.name}】")

            # 取得菜單
            result = await self.session.execute(
                select(Menu)
                .where(Menu.store_id == store.id)
                .options(
                    selectinload(Menu.categories).selectinload(MenuCategory.items)
                )
            )
            menu = result.scalar_one_or_none()

            if not menu:
                lines.append("  (尚無菜單)")
                continue

            for cat in menu.categories:
                if not cat.items:
                    continue

                if cat.name:
                    lines.append(f"▸ {cat.name}")

                for item in cat.items:
                    if item.variants:
                        var_strs = [f"{v.get('name', '')}${int(v.get('price', 0))}" for v in item.variants]
                        lines.append(f"  {item.name} {'/'.join(var_strs)}")
                    else:
                        lines.append(f"  {item.name} ${int(item.price)}")

        return "\n".join(lines) if len(lines) > 1 else "📋 今日尚未設定店家菜單"

    async def _get_session_summary_by_id(self, session_id: UUID) -> str:
        """產生點餐摘要"""
        # 重新載入 session 的訂單
        session_with_orders = await self.session_repo.get_with_orders(session_id)
        if not session_with_orders:
            return "📋 本次點餐沒有任何訂單"

        orders = session_with_orders.orders
        if not orders:
            return "📋 本次點餐沒有任何訂單"

        lines = ["📋 點餐摘要", ""]
        grand_total = Decimal(0)
        item_counts = {}

        for order in orders:
            user_name = order.user.display_name if order.user else "未知"
            user_total = int(order.total_amount)

            lines.append(f"👤 {user_name}（${user_total}）")

            for item in order.items:
                item_text = f"  • {item.name}"
                if item.note:
                    item_text += f"（{item.note}）"
                if item.quantity > 1:
                    item_text += f" x{item.quantity}"
                item_text += f" ${int(item.subtotal)}"
                lines.append(item_text)

                # 統計（只以名稱統計，不含備註）
                item_key = item.name
                item_counts[item_key] = item_counts.get(item_key, 0) + item.quantity

            lines.append("")
            grand_total += order.total_amount

        # 品項統計
        lines.append("📦 品項統計")
        for name, count in sorted(item_counts.items(), key=lambda x: -x[1]):
            lines.append(f"  • {name} x{count}")

        lines.append("")
        lines.append(f"💰 總金額：${int(grand_total)}")
        lines.append(f"👥 共 {len(orders)} 人點餐")

        return "\n".join(lines)

    # ========== AI 對話處理 ==========

    async def _handle_ai_chat(
        self,
        user: User,
        group: Group,
        active_session: Optional[OrderSession],
        text: str,
        reply_token: str,
    ) -> None:
        """處理 AI 對話"""
        from app.broadcast import emit_chat_message

        # 記錄使用者訊息
        chat_msg = ChatMessage(
            group_id=group.id,
            user_id=user.id,
            session_id=active_session.id if active_session else None,
            role="user",
            content=text,
        )
        await self.chat_repo.create(chat_msg)

        # 廣播使用者訊息
        await emit_chat_message(str(group.id), {
            "group_id": str(group.id),
            "user_id": str(user.id),
            "display_name": user.display_name or "使用者",
            "role": "user",
            "content": text,
        })

        try:
            # 取得系統提示詞
            system_prompt = await self._get_group_system_prompt()

            # 取得今日店家與菜單
            today_stores = await self.today_store_repo.get_today_stores(group.id)
            menus_context = await self._build_menus_context(today_stores)

            # 取得目前訂單狀態
            session_orders = []
            if active_session:
                session_with_orders = await self.session_repo.get_with_orders(active_session.id)
                if session_with_orders:
                    for order in session_with_orders.orders:
                        session_orders.append({
                            "display_name": order.user.display_name if order.user else "未知",
                            "items": [
                                {
                                    "name": item.name,
                                    "quantity": item.quantity,
                                    "price": float(item.unit_price),
                                    "subtotal": float(item.subtotal),
                                    "note": item.note,
                                }
                                for item in order.items
                            ],
                            "total": float(order.total_amount),
                        })

            # 取得對話歷史（只取當前 session 的）
            history_limit = settings.chat_history_limit
            history = await self.chat_repo.get_group_messages(
                group.id,
                limit=history_limit,
                session_id=active_session.id if active_session else None,
            )

            # 輸入過濾
            sanitized_text, trigger_reasons = sanitize_user_input(text)
            if trigger_reasons:
                await self._log_security_event(
                    line_user_id=user.line_user_id,
                    display_name=user.display_name,
                    line_group_id=group.line_group_id,
                    original_message=text,
                    sanitized_message=sanitized_text,
                    trigger_reasons=trigger_reasons,
                    context_type="group",
                )
                # 有可疑內容，靜默不回應
                return

            # 呼叫 AI
            ai_response = await self.ai_service.chat(
                message=sanitized_text,
                system_prompt=system_prompt,
                context={
                    "mode": "group_ordering" if active_session else "group_idle",
                    "user_name": user.display_name or "使用者",
                    "today_stores": [
                        {"id": str(ts.store_id), "name": ts.store.name if ts.store else None}
                        for ts in today_stores
                    ],
                    "menus": menus_context,
                    "session_orders": session_orders,
                    "user_preferences": user.preferences,
                },
                history=[
                    {
                        "role": msg.role,
                        "name": msg.user.display_name if msg.user else "系統",
                        "content": msg.content,
                    }
                    for msg in history[-history_limit:]
                ],
            )

            response_text = ai_response.get("message", "").strip()

            # AI 回覆空訊息表示不需要回應，直接返回
            if not response_text and not ai_response.get("actions"):
                logger.warning(f"AI returned empty response for message: {text}")
                return

            ai_message_only = response_text  # 保留 AI 原始訊息（不含摘要）

            # 處理 AI 動作
            actions = ai_response.get("actions", [])
            if actions and active_session:
                action_results = await self._execute_group_actions(
                    user, group, active_session, today_stores, actions
                )
                # 檢查動作類型
                has_create_or_update = any(
                    a.get("type") in ["group_create_order", "group_remove_item", "group_update_order"]
                    for a in actions
                )
                has_cancel = any(a.get("type") == "group_cancel_order" for a in actions)
                has_success = any(r.get("success") for r in action_results)

                # 附加錯誤訊息
                for result in action_results:
                    if result.get("error"):
                        response_text += f"\n\n⚠️ {result['error']}"

                # 如果有成功的訂單動作，附加摘要
                if (has_create_or_update or has_cancel) and has_success:
                    await self.session.flush()
                    summary = await self._get_session_summary_by_id(active_session.id)
                    response_text += f"\n\n{summary}"

            # 如果最終訊息為空，不回覆也不記錄
            if not response_text.strip():
                return

            # 記錄 AI 回應（只保存對話訊息，不含訂單摘要）
            if ai_message_only:
                ai_msg = ChatMessage(
                    group_id=group.id,
                    session_id=active_session.id if active_session else None,
                    role="assistant",
                    content=ai_message_only,
                )
                await self.chat_repo.create(ai_msg)

                # 廣播 AI 回應
                await emit_chat_message(str(group.id), {
                    "group_id": str(group.id),
                    "display_name": "呷爸",
                    "role": "assistant",
                    "content": ai_message_only,
                })

            await self.reply_message(reply_token, response_text)

        except Exception as e:
            logger.error(f"AI chat error: {e}", exc_info=True)
            await self.reply_message(reply_token, "抱歉，我現在有點忙，請稍後再試。")

    async def _build_menus_context(self, today_stores: list) -> dict:
        """建構菜單上下文"""
        menus = {}
        for ts in today_stores:
            store = ts.store
            if not store:
                continue

            result = await self.session.execute(
                select(Menu)
                .where(Menu.store_id == store.id)
                .options(
                    selectinload(Menu.categories).selectinload(MenuCategory.items)
                )
            )
            menu = result.scalar_one_or_none()

            if menu:
                menus[str(store.id)] = {
                    "name": store.name,
                    "categories": [
                        {
                            "name": cat.name,
                            "items": [
                                {
                                    "id": str(item.id),
                                    "name": item.name,
                                    "price": float(item.price),
                                    "variants": item.variants,
                                    "description": item.description,
                                }
                                for item in cat.items
                            ],
                        }
                        for cat in menu.categories
                    ],
                }

        return menus

    # ========== 動作執行 ==========

    async def _execute_group_actions(
        self,
        user: User,
        group: Group,
        session: OrderSession,
        today_stores: list,
        actions: list,
    ) -> list:
        """執行群組點餐動作"""
        from app.broadcast import emit_order_update, flush_events

        results = []
        broadcast_action = None  # 記錄最後一個成功動作的類型

        for action in actions:
            action_type = action.get("type")
            action_data = action.get("data", {})

            try:
                if action_type == "group_create_order":
                    result = await self._action_create_order(
                        user, session, today_stores, action_data
                    )
                    if result.get("success"):
                        broadcast_action = "created"
                elif action_type == "group_remove_item":
                    result = await self._action_remove_item(
                        user, session, action_data
                    )
                    if result.get("success"):
                        broadcast_action = "updated"
                elif action_type == "group_cancel_order":
                    result = await self._action_cancel_order(user, session)
                    if result.get("success"):
                        broadcast_action = "cancelled"
                elif action_type == "group_update_order":
                    result = await self._action_update_order(
                        user, session, today_stores, action_data
                    )
                    if result.get("success"):
                        broadcast_action = "updated"
                else:
                    result = {"success": True, "message": "No action needed"}

                results.append(result)
            except Exception as e:
                logger.error(f"Action {action_type} error: {e}")
                results.append({"success": False, "error": str(e)})

        # 如果有成功的動作，先 commit 再廣播
        if broadcast_action:
            await self.session.commit()
            await emit_order_update(str(group.id), {
                "group_id": str(group.id),
                "action": broadcast_action,
                "user_id": str(user.id),
                "display_name": user.display_name,
            })
            await flush_events()

        return results

    async def _action_create_order(
        self,
        user: User,
        session: OrderSession,
        today_stores: list,
        data: dict,
    ) -> dict:
        """建立訂單"""
        items = data.get("items", [])
        if not items:
            return {"success": False, "error": "沒有品項"}

        # 取得或建立使用者訂單
        order = await self.order_repo.get_by_session_and_user(session.id, user.id)

        if not order:
            # 取得第一個今日店家
            store_id = today_stores[0].store_id if today_stores else None
            if not store_id:
                return {"success": False, "error": "今日尚未設定店家"}

            order = Order(
                session_id=session.id,
                user_id=user.id,
                store_id=store_id,
            )
            order = await self.order_repo.create(order)

        # 新增品項
        for item_data in items:
            item_name = item_data.get("name", "")
            quantity = item_data.get("quantity", 1)
            note = item_data.get("note", "")
            category = item_data.get("category", None)  # AI 可選擇性提供類別

            # 從菜單找價格（有類別會更精確）
            price = await self._find_item_price(today_stores, item_name, category)

            # 找不到價格（品項不在菜單中）
            if price == 0:
                return {"success": False, "error": f"菜單中找不到「{item_name}」"}

            order_item = OrderItem(
                order_id=order.id,
                name=item_name,
                quantity=quantity,
                unit_price=Decimal(str(price)),
                subtotal=Decimal(str(price * quantity)),
                note=note,
            )
            await self.order_item_repo.create(order_item)

        # 重新計算總金額
        await self.order_repo.calculate_total(order)

        # 確保資料已寫入資料庫
        await self.session.flush()

        return {"success": True, "order_id": str(order.id)}

    async def _action_remove_item(
        self,
        user: User,
        session: OrderSession,
        data: dict,
    ) -> dict:
        """移除品項"""
        item_name = data.get("item_name", "")
        quantity = data.get("quantity", 1)

        order = await self.order_repo.get_by_session_and_user(session.id, user.id)
        if not order:
            return {"success": False, "error": "你目前沒有訂單"}

        # 找到品項
        for item in order.items:
            if item.name == item_name or item_name in item.name:
                if quantity >= item.quantity:
                    await self.order_item_repo.delete(item)
                else:
                    item.quantity -= quantity
                    item.subtotal = item.unit_price * item.quantity
                    await self.order_item_repo.update(item)

                # 重新計算總金額
                await self.order_repo.calculate_total(order)

                # 如果沒有品項了，刪除訂單
                if not order.items:
                    await self.order_repo.delete(order)

                await self.session.flush()
                return {"success": True}

        return {"success": False, "error": f"找不到品項：{item_name}"}

    async def _action_cancel_order(
        self,
        user: User,
        session: OrderSession,
    ) -> dict:
        """取消訂單"""
        order = await self.order_repo.get_by_session_and_user(session.id, user.id)
        if not order:
            return {"success": False, "error": "你目前沒有訂單"}

        await self.order_repo.delete(order)
        await self.session.flush()
        return {"success": True}

    async def _action_update_order(
        self,
        user: User,
        session: OrderSession,
        today_stores: list,
        data: dict,
    ) -> dict:
        """更新訂單（替換品項）"""
        old_item = data.get("old_item", "")
        new_item = data.get("new_item", {})

        # 先移除舊品項
        result = await self._action_remove_item(user, session, {"item_name": old_item, "quantity": 999})
        if not result.get("success"):
            return result

        # 新增新品項
        return await self._action_create_order(user, session, today_stores, {"items": [new_item]})

    async def _execute_personal_actions(
        self,
        user: User,
        actions: list,
    ) -> list[str]:
        """執行個人模式動作，回傳額外訊息列表"""
        extra_messages = []

        for action in actions:
            action_type = action.get("type")
            action_data = action.get("data", {})

            if action_type == "update_user_profile":
                # 更新使用者偏好
                user.preferences = {**user.preferences, **action_data}
                await self.user_repo.update(user)

            elif action_type == "personal_query_preferences":
                # 查詢偏好設定
                extra_messages.append(self._get_preferences_summary(user))

            elif action_type == "personal_query_groups":
                # 查詢所屬群組
                summary = await self._get_user_groups_summary(user)
                extra_messages.append(summary)

            elif action_type == "personal_query_orders":
                # 查詢歷史訂單
                summary = await self._get_order_history_summary(user)
                extra_messages.append(summary)

            elif action_type == "personal_clear_preferences":
                # 清除偏好設定
                result = await self._clear_user_preferences(user)
                extra_messages.append(result)

        return extra_messages

    async def _find_item_price(
        self, today_stores: list, item_name: str, category: str = None
    ) -> float:
        """從今日菜單找品項價格

        Args:
            today_stores: 今日店家列表
            item_name: 品項名稱
            category: 類別名稱（可選，如「便當」「單點類」）

        搜尋優先順序：
        1. 若有指定類別，在該類別中精確匹配
        2. 若有指定類別，在該類別中部分匹配
        3. 無類別時，精確匹配名稱
        4. 無類別時，部分匹配
        """
        all_items = []
        for ts in today_stores:
            result = await self.session.execute(
                select(MenuItem, MenuCategory.name.label("category_name"))
                .join(MenuCategory)
                .join(Menu)
                .where(Menu.store_id == ts.store_id)
            )
            for row in result.all():
                all_items.append({
                    "item": row[0],
                    "category": row[1],
                })

        # 若有指定類別，優先在該類別中搜尋
        if category:
            # 類別內精確匹配
            for data in all_items:
                if data["category"] == category and data["item"].name == item_name:
                    return float(data["item"].price)
            # 類別內部分匹配
            for data in all_items:
                if data["category"] == category and item_name in data["item"].name:
                    return float(data["item"].price)

        # 無類別或類別內找不到：精確匹配
        for data in all_items:
            if data["item"].name == item_name:
                return float(data["item"].price)

        # 部分匹配
        for data in all_items:
            if item_name in data["item"].name:
                return float(data["item"].price)

        return 0

    # ========== 系統提示詞 ==========

    async def _load_prompt_from_db(self, name: str) -> str:
        """從快取或 DB 讀取提示詞（無 fallback，必須有資料）"""
        # 先查快取
        cached = CacheService.get_prompt(name)
        if cached:
            return cached

        # 查 DB
        prompt = await self.prompt_repo.get_by_name(name)
        if prompt:
            CacheService.set_prompt(name, prompt.content)
            return prompt.content

        # 沒有資料就報錯
        raise ValueError(f"找不到提示詞：{name}，請確認資料庫已執行 alembic upgrade")

    async def _get_group_system_prompt(self) -> str:
        """取得群組點餐系統提示詞"""
        return await self._load_prompt_from_db("group_ordering")

    async def _get_personal_system_prompt(self) -> str:
        """取得個人模式系統提示詞"""
        return await self._load_prompt_from_db("personal_preferences")

    async def _get_application_system_prompt(self) -> str:
        """取得群組申請系統提示詞"""
        return await self._load_prompt_from_db("group_intro")

    async def _log_security_event(
        self,
        line_user_id: str,
        display_name: Optional[str],
        line_group_id: Optional[str],
        original_message: str,
        sanitized_message: str,
        trigger_reasons: list[str],
        context_type: str,
    ) -> None:
        """記錄安全日誌並檢查是否需要自動封鎖"""
        from datetime import datetime, timezone

        log = SecurityLog(
            line_user_id=line_user_id,
            display_name=display_name,
            line_group_id=line_group_id,
            original_message=original_message,
            sanitized_message=sanitized_message,
            trigger_reasons=trigger_reasons,
            context_type=context_type,
        )
        await self.security_log_repo.create(log)
        await self.session.commit()
        logger.warning(
            f"Security event logged: user={line_user_id}, "
            f"reasons={trigger_reasons}, "
            f"original_len={len(original_message)}"
        )

        # 檢查是否超過封鎖閾值
        violation_count = await self.security_log_repo.get_total_count(line_user_id=line_user_id)
        if violation_count >= settings.security_ban_threshold:
            # 自動封鎖使用者
            user = await self.user_repo.get_by_line_user_id(line_user_id)
            if user and not user.is_banned:
                user.is_banned = True
                user.banned_at = datetime.now(timezone.utc)
                await self.session.commit()
                logger.warning(
                    f"User auto-banned: {line_user_id} (violations: {violation_count})"
                )

    # ========== Pending 群組處理 ==========

    async def _handle_pending_group_chat(
        self,
        user: User,
        group: Group,
        text: str,
        reply_token: str,
    ) -> None:
        """處理 pending 群組訊息

        統一入口：用戶輸入 jaba/help 時根據狀態回應
        - 有 pending 申請 → 顯示等待審核
        - 有 rejected 申請 → 顯示被拒 + 引導重新申請
        - 無申請 → AI 引導新申請
        """
        # 記錄成員（即使群組尚未啟用，也記錄互動的用戶）
        _, is_new_member = await self.member_repo.add_member(group.id, user.id)
        if is_new_member:
            from app.broadcast import emit_group_update
            await emit_group_update({"action": "member_added", "group_id": str(group.id)})

        text_lower = text.strip().lower()
        help_keywords = ["help", "jaba", "呷爸", "@jaba", "@呷爸"]
        is_help_request = text_lower in help_keywords

        # 取得最新申請狀態
        latest_app = await self.application_repo.get_latest_by_line_group_id(
            group.line_group_id
        )

        if latest_app:
            if latest_app.status == "pending":
                # 有待審核申請
                if is_help_request:
                    await self._handle_pending_application_response(
                        group, latest_app, text_lower, reply_token
                    )
                # 其他訊息不回應（等審核中）
                return

            elif latest_app.status == "rejected":
                # 被拒絕的申請
                if is_help_request:
                    # 顯示拒絕狀態 + 引導重新申請
                    response = self._build_rejected_application_message(latest_app)
                    await self.reply_message(reply_token, response)

                    # 寫入上下文記錄，讓 AI 知道用戶已確認拒絕並準備重新申請
                    context_msg = ChatMessage(
                        group_id=group.id,
                        role="assistant",
                        content=f"[系統記錄] 用戶查詢了申請狀態。之前的申請「{latest_app.group_name}」已被拒絕（原因：{latest_app.review_note or '未說明'}）。用戶現在可以提供新的申請資料重新申請。",
                    )
                    await self.chat_repo.create(context_msg)

                    # 將申請標記為 archived，下次用戶輸入就進入新申請流程
                    latest_app.status = "archived"
                    await self.session.flush()
                    return
                # 其他訊息：讓 AI 處理重新申請（對話歷史已有上下文）
                await self._handle_application_with_ai(
                    user, group, text, reply_token, is_reapplication=True
                )
                return

            # archived 或其他狀態：視為無申請，可以重新申請

        # 無申請或已歸檔 → AI 引導新申請
        await self._handle_application_with_ai(user, group, text, reply_token)

    async def _handle_pending_application_response(
        self,
        group: Group,
        application: GroupApplication,
        text: str,
        reply_token: str,
    ) -> None:
        """顯示待審核申請狀態"""
        response = (
            "🍱 呷爸 - AI 午餐訂便當助手\n\n"
            "📋 申請狀態\n"
            f"群組名稱：{application.group_name or '未提供'}\n"
            f"狀態：⏳ 待審核\n"
            f"申請時間：{application.created_at.strftime('%Y/%m/%d %H:%M') if application.created_at else '未知'}\n\n"
            "請耐心等待管理員審核～\n"
            "想查詢進度，隨時輸入「jaba」即可！"
        )
        await self.reply_message(reply_token, response)

    def _build_rejected_application_message(
        self,
        application: GroupApplication,
    ) -> str:
        """建立被拒絕申請的訊息"""
        rejection_note = f"\n拒絕原因：{application.review_note}" if application.review_note else ""
        return (
            "🍱 呷爸 - AI 午餐訂便當助手\n\n"
            "📋 申請狀態\n"
            f"群組名稱：{application.group_name or '未提供'}\n"
            f"狀態：❌ 已被拒絕\n"
            f"審核時間：{application.reviewed_at.strftime('%Y/%m/%d %H:%M') if application.reviewed_at else '未知'}"
            f"{rejection_note}\n\n"
            "如需重新申請，請直接告訴我：\n"
            "1. 群組名稱（如「XX公司午餐團」）\n"
            "2. 聯絡方式（LINE ID 或 Email）\n"
            "3. 群組代碼（自訂，管理員綁定用）"
        )

    async def _handle_application_with_ai(
        self,
        user: User,
        group: Group,
        text: str,
        reply_token: str,
        is_reapplication: bool = False,
    ) -> None:
        """使用 AI 引導申請開通（無申請或已被拒絕時）"""
        # 記錄使用者訊息
        chat_msg = ChatMessage(
            group_id=group.id,
            user_id=user.id,
            role="user",
            content=text,
        )
        await self.chat_repo.create(chat_msg)

        try:
            # 取得申請引導提示詞
            system_prompt = await self._get_application_system_prompt()

            # 取得對話歷史
            history_limit = settings.chat_history_limit
            history = await self.chat_repo.get_group_messages(group.id, limit=history_limit)

            # 重新申請時，加入上下文提示
            if is_reapplication:
                reapply_context = {
                    "role": "system",
                    "name": "系統",
                    "content": "（此群組之前的申請已被拒絕，使用者現在要重新申請。請直接處理使用者提供的申請資料，不需要再自我介紹。）",
                }

            # 輸入過濾
            sanitized_text, trigger_reasons = sanitize_user_input(text)
            if trigger_reasons:
                await self._log_security_event(
                    line_user_id=user.line_user_id,
                    display_name=user.display_name,
                    line_group_id=group.line_group_id,
                    original_message=text,
                    sanitized_message=sanitized_text,
                    trigger_reasons=trigger_reasons,
                    context_type="group",
                )
                # 有可疑內容，靜默不回應
                return

            # 建立對話歷史
            chat_history = [
                {
                    "role": msg.role,
                    "name": msg.user.display_name if msg.user else "系統",
                    "content": msg.content,
                }
                for msg in history[-history_limit:]
            ]

            # 重新申請時，在歷史前加入上下文
            if is_reapplication:
                chat_history = [reapply_context] + chat_history

            # 呼叫 AI
            # 注意：不傳遞 group_id 給 AI，避免 AI 誤將內部 ID 告知使用者
            # 使用者應透過輸入「id」指令取得正確的 LINE 群組 ID
            ai_response = await self.ai_service.chat(
                message=sanitized_text,
                system_prompt=system_prompt,
                context={
                    "mode": "group_application",
                    "user_name": user.display_name or "使用者",
                },
                history=chat_history,
            )

            response_text = ai_response.get("message", "").strip()

            # AI 回覆空訊息表示不需要回應
            if not response_text and not ai_response.get("actions"):
                return

            # 處理 AI 動作
            actions = ai_response.get("actions", [])
            if actions:
                action_results = await self._execute_application_actions(
                    user, group, actions
                )
                # 附加動作結果訊息
                for result in action_results:
                    if result.get("error"):
                        response_text += f"\n\n⚠️ {result['error']}"
                    elif result.get("message"):
                        response_text += f"\n\n{result['message']}"

            # 如果最終訊息為空，不回覆
            if not response_text.strip():
                return

            # 記錄 AI 回應
            ai_msg = ChatMessage(
                group_id=group.id,
                role="assistant",
                content=response_text,
            )
            await self.chat_repo.create(ai_msg)

            await self.reply_message(reply_token, response_text)

        except Exception as e:
            logger.error(f"Pending group chat error: {e}", exc_info=True)
            # 出錯時顯示傳統申請引導
            await self.reply_message(reply_token, self._guide_to_apply(is_group=True))

    async def _execute_application_actions(
        self,
        user: User,
        group: Group,
        actions: list,
    ) -> list:
        """執行群組申請動作"""
        import uuid

        results = []

        for action in actions:
            action_type = action.get("type")
            action_data = action.get("data", {})

            try:
                if action_type == "submit_application":
                    # 提交群組申請
                    group_name = action_data.get("group_name", "")
                    contact_info = action_data.get("contact_info", "")
                    group_code = action_data.get("group_code", "")

                    if not group_name or not contact_info or not group_code:
                        results.append({
                            "success": False,
                            "error": "申請資料不完整，請提供群組名稱、聯絡方式和群組代碼"
                        })
                        continue

                    # 檢查是否已有 pending 申請
                    existing = await self.application_repo.get_pending_by_line_group_id(
                        group.line_group_id
                    )
                    if existing:
                        results.append({
                            "success": False,
                            "error": "此群組已有待審核的申請，請等待管理員審核"
                        })
                        continue

                    # 建立申請
                    application = GroupApplication(
                        id=uuid.uuid4(),
                        line_group_id=group.line_group_id,
                        group_name=group_name,
                        contact_info=contact_info,
                        group_code=group_code,
                        status="pending",
                    )
                    await self.application_repo.create(application)
                    await self.session.commit()

                    # 廣播給超管後台
                    from app.broadcast import emit_application_update
                    await emit_application_update({
                        "action": "new",
                        "application": {
                            "id": str(application.id),
                            "line_group_id": application.line_group_id,
                            "group_name": application.group_name,
                            "contact_info": application.contact_info,
                            "group_code": application.group_code,
                            "status": application.status,
                        }
                    })

                    results.append({"success": True})

                else:
                    results.append({"success": True, "message": "No action needed"})

            except Exception as e:
                logger.error(f"Application action {action_type} error: {e}")
                results.append({"success": False, "error": str(e)})

        return results

    # ========== 事件處理 ==========

    async def handle_join(self, group_id: str, reply_token: str) -> None:
        """處理加入群組事件"""
        group = await self.group_repo.get_or_create(group_id)

        # 嘗試取得群組名稱
        group_name = await self.get_group_name(group_id)
        if group_name:
            group.name = group_name
            await self.group_repo.update(group)

        if group.status == "active":
            # 已啟用的群組
            await self.reply_message(
                reply_token,
                "哇係呷爸！🎉\n\n"
                "我是你們的點餐小幫手，可以幫大家統計訂單。\n\n"
                "輸入「開單」開始點餐\n"
                "輸入「結單」結束點餐\n"
                "或直接跟我說你要吃什麼！",
            )
        elif group.status == "inactive":
            # 曾被踢出的群組，提供選擇
            display_name = group.name or "此群組"
            await self._reply_with_quick_reply(
                reply_token,
                f"🔄 偵測到「{display_name}」曾經使用過呷爸服務\n\n"
                "請選擇要如何處理：\n\n"
                "• 恢復舊設定：保留原本的店家和設定，立即可用\n"
                "• 重新申請：需重新審核，若使用不同群組代碼，原本的群組專屬店家將會失聯",
                [
                    QuickReplyItem(
                        action=PostbackAction(
                            label="✅ 恢復舊設定",
                            data=f"action=rejoin_restore&group_id={group_id}",
                        )
                    ),
                    QuickReplyItem(
                        action=PostbackAction(
                            label="📝 重新申請",
                            data=f"action=rejoin_reapply&group_id={group_id}",
                        )
                    ),
                ],
            )
        elif group.status == "suspended":
            # 被超管停用的群組
            await self.reply_message(
                reply_token,
                "⚠️ 此群組已被管理員停用\n\n"
                "如有疑問，請聯繫系統管理員。",
            )
        else:
            # pending 或其他狀態，要求申請
            await self.reply_message(
                reply_token,
                "哩賀！哇係呷爸 🙋\n\n"
                "這個群組尚未開通點餐功能。\n\n"
                "📝 申請開通方式：\n\n"
                "【方式一】直接在這裡申請\n"
                "請告訴我以下資訊：\n"
                "1. 群組名稱（如「XX公司午餐團」）\n"
                "2. 聯絡方式（LINE ID 或 Email）\n"
                "3. 群組代碼（自訂，管理員綁定用）\n\n"
                "【方式二】網頁申請\n"
                f"前往 {APPLY_URL}\n"
                "輸入「id」可取得群組 ID\n\n"
                "審核通過後即可開始使用！",
            )

    async def handle_leave(self, group_id: str) -> None:
        """處理離開群組事件"""
        group = await self.group_repo.get_by_line_group_id(group_id)
        if group:
            group.status = "inactive"
            await self.group_repo.update(group)

    async def handle_postback(
        self,
        user_id: str,
        group_id: Optional[str],
        data: str,
        reply_token: str,
    ) -> None:
        """處理 Postback 事件"""
        params = dict(item.split("=") for item in data.split("&") if "=" in item)
        action = params.get("action")

        if action == "order":
            item_name = params.get("item")
            await self.reply_message(reply_token, f"已記錄您點的：{item_name}")
        elif action == "cancel":
            await self.reply_message(reply_token, "已取消")
        elif action == "rejoin_restore":
            # 恢復舊設定
            target_group_id = params.get("group_id")
            await self._handle_rejoin_restore(target_group_id, reply_token)
        elif action == "rejoin_reapply":
            # 重新申請
            target_group_id = params.get("group_id")
            await self._handle_rejoin_reapply(target_group_id, reply_token)
        else:
            logger.warning(f"Unknown postback action: {action}")

    async def _handle_rejoin_restore(
        self, group_id: str, reply_token: str
    ) -> None:
        """處理重新加入群組 - 恢復舊設定"""
        group = await self.group_repo.get_by_line_group_id(group_id)
        if not group:
            await self.reply_message(reply_token, "❌ 找不到群組記錄")
            return

        if group.status != "inactive":
            await self.reply_message(reply_token, "⚠️ 此群組狀態已變更，請重新操作")
            return

        # 恢復為 active 狀態
        group.status = "active"
        await self.group_repo.update(group)

        await self.reply_message(
            reply_token,
            "✅ 已恢復舊設定！\n\n"
            "哇係呷爸！🎉\n"
            "原本的店家和設定都還在，可以開始點餐了！\n\n"
            "輸入「開單」開始點餐\n"
            "輸入「結單」結束點餐\n"
            "或直接跟我說你要吃什麼！",
        )

    async def _handle_rejoin_reapply(
        self, group_id: str, reply_token: str
    ) -> None:
        """處理重新加入群組 - 重新申請"""
        group = await self.group_repo.get_by_line_group_id(group_id)
        if not group:
            await self.reply_message(reply_token, "❌ 找不到群組記錄")
            return

        if group.status != "inactive":
            await self.reply_message(reply_token, "⚠️ 此群組狀態已變更，請重新操作")
            return

        # 設為 pending 狀態，需要重新審核
        group.status = "pending"
        await self.group_repo.update(group)

        await self.reply_message(
            reply_token,
            "📝 已切換為重新申請模式\n\n"
            "請直接告訴我以下資訊：\n"
            "1. 群組名稱（如「XX公司午餐團」）\n"
            "2. 聯絡方式（LINE ID 或 Email）\n"
            "3. 群組代碼（自訂，管理員綁定用）\n\n"
            "💡 提醒：若使用不同群組代碼，原本的群組專屬店家將無法使用。",
        )
