"""定時任務排程器"""
import logging
import os
from datetime import datetime

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.database import get_db_context
from app.repositories.chat_repo import ChatRepository

logger = logging.getLogger(__name__)

# 全域排程器實例
scheduler = AsyncIOScheduler()


async def cleanup_old_chat_messages():
    """清理超過一年的對話記錄"""
    logger.info(f"[{datetime.now()}] 開始定期清理舊對話記錄...")

    try:
        async with get_db_context() as db:
            repo = ChatRepository(db)

            # 取得統計
            stats = await repo.get_stats()
            logger.info(f"  清理前: {stats['total_messages']} 筆訊息")
            logger.info(f"  超過一年: {stats['messages_older_than_1_year']} 筆")

            if stats["messages_older_than_1_year"] > 0:
                deleted = await repo.cleanup_old_messages(retention_days=365)
                await db.commit()
                logger.info(f"  已刪除: {deleted} 筆")
            else:
                logger.info("  無需清理")

    except Exception as e:
        logger.error(f"清理對話記錄失敗: {e}")

    logger.info(f"[{datetime.now()}] 清理完成")


async def close_open_sessions():
    """每天下午結束還開著的點餐；沒有任何訂單的單直接刪除"""
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    from app.models.order import OrderSession

    try:
        async with get_db_context() as db:
            result = await db.execute(
                select(OrderSession)
                .where(OrderSession.status == "ordering")
                .options(selectinload(OrderSession.orders))
            )
            closed = deleted = 0
            for s in result.scalars().all():
                if s.orders:
                    s.status = "ended"
                    s.ended_at = datetime.now()
                    closed += 1
                else:
                    await db.delete(s)
                    deleted += 1
            await db.commit()
            logger.info(f"自動結單：結束 {closed} 筆、刪除空單 {deleted} 筆")
    except Exception as e:
        logger.error(f"自動結單失敗: {e}")


def start_scheduler():
    """啟動排程器"""
    # 每月1號凌晨3點執行清理
    scheduler.add_job(
        cleanup_old_chat_messages,
        CronTrigger(day=1, hour=3, minute=0),
        id="cleanup_chat_messages",
        name="清理舊對話記錄",
        replace_existing=True,
    )

    # 每天自動結單（預設 15:00，台北時間）
    scheduler.add_job(
        close_open_sessions,
        CronTrigger(hour=int(os.getenv("AUTO_CLOSE_HOUR", "15")), minute=0, timezone="Asia/Taipei"),
        id="close_open_sessions",
        name="每日自動結單",
        replace_existing=True,
    )

    scheduler.start()
    logger.info("排程器已啟動，已設定每月清理任務")


def stop_scheduler():
    """停止排程器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("排程器已停止")
