"""LINE Webhook 路由"""
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Header
from linebot.v3.webhook import WebhookParser
from linebot.v3.exceptions import InvalidSignatureError
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    JoinEvent,
    LeaveEvent,
    PostbackEvent,
)
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.services import LineService

logger = logging.getLogger("jaba.webhook")

router = APIRouter(prefix="/api/webhook", tags=["webhook"])

# LINE Webhook Parser
parser = WebhookParser(settings.line_channel_secret)


@router.post("/line")
async def line_callback(
    request: Request,
    x_line_signature: str = Header(...),
    db: AsyncSession = Depends(get_db),
):
    """LINE Webhook 回調"""
    body = await request.body()
    body_str = body.decode("utf-8")

    try:
        events = parser.parse(body_str, x_line_signature)
    except InvalidSignatureError:
        logger.warning("Invalid LINE signature")
        raise HTTPException(status_code=400, detail="Invalid signature")

    service = LineService(db)

    for event in events:
        try:
            if isinstance(event, MessageEvent):
                if isinstance(event.message, TextMessageContent):
                    await handle_text_message(service, event)
            elif isinstance(event, JoinEvent):
                await handle_join_event(service, event)
            elif isinstance(event, LeaveEvent):
                await handle_leave_event(service, event)
            elif isinstance(event, PostbackEvent):
                await handle_postback_event(service, event)
        except Exception as e:
            logger.error(f"Error handling event: {e}", exc_info=True)

    return {"status": "ok"}


async def handle_text_message(service: LineService, event: MessageEvent):
    """處理文字訊息"""
    text = event.message.text
    user_id = event.source.user_id

    # 判斷來源類型
    source_type = event.source.type
    group_id = None

    if source_type == "group":
        group_id = event.source.group_id
    elif source_type == "room":
        group_id = event.source.room_id

    logger.info(f"Text message from {user_id} in {source_type}: {text[:50]}")

    # 處理訊息
    await service.handle_message(
        user_id=user_id,
        group_id=group_id,
        text=text,
        reply_token=event.reply_token,
    )


async def handle_join_event(service: LineService, event: JoinEvent):
    """處理加入群組事件"""
    source_type = event.source.type

    if source_type == "group":
        group_id = event.source.group_id
    elif source_type == "room":
        group_id = event.source.room_id
    else:
        return

    logger.info(f"Bot joined {source_type}: {group_id}")

    await service.handle_join(
        group_id=group_id,
        reply_token=event.reply_token,
    )


async def handle_leave_event(service: LineService, event: LeaveEvent):
    """處理離開群組事件"""
    source_type = event.source.type

    if source_type == "group":
        group_id = event.source.group_id
    elif source_type == "room":
        group_id = event.source.room_id
    else:
        return

    logger.info(f"Bot left {source_type}: {group_id}")

    await service.handle_leave(group_id=group_id)


async def handle_postback_event(service: LineService, event: PostbackEvent):
    """處理 Postback 事件"""
    data = event.postback.data
    user_id = event.source.user_id

    source_type = event.source.type
    group_id = None

    if source_type == "group":
        group_id = event.source.group_id
    elif source_type == "room":
        group_id = event.source.room_id

    logger.info(f"Postback from {user_id}: {data}")

    await service.handle_postback(
        user_id=user_id,
        group_id=group_id,
        data=data,
        reply_token=event.reply_token,
    )
