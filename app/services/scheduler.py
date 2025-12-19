"""定時任務排程器"""
import logging
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

    scheduler.start()
    logger.info("排程器已啟動，已設定每月清理任務")


def stop_scheduler():
    """停止排程器"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("排程器已停止")
