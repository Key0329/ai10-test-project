"""排程任務：定期清除過期 log。"""

import asyncio
import logging
from datetime import datetime, timedelta, timezone

from db import get_db

logger = logging.getLogger("scheduler")

# 清除幾天前的 log（預設 7 天）
LOG_RETENTION_DAYS = 7


async def _cleanup_old_logs() -> None:
    """刪除 job_logs 中超過 LOG_RETENTION_DAYS 天的紀錄，以及對應的已結束 jobs。"""
    cutoff = (datetime.now(timezone.utc) - timedelta(days=LOG_RETENTION_DAYS)).isoformat()

    db = await get_db()
    try:
        # 刪除舊 log 紀錄
        cursor = await db.execute(
            "DELETE FROM job_logs WHERE timestamp < ?",
            (cutoff,),
        )
        deleted_logs = cursor.rowcount

        # 刪除超過保留期且已結束的 jobs（queued/running 等不刪）
        cursor = await db.execute(
            """DELETE FROM jobs
               WHERE created_at < ?
               AND status IN ('completed', 'failed', 'cancelled')""",
            (cutoff,),
        )
        deleted_jobs = cursor.rowcount

        await db.commit()
        logger.info(
            f"[排程清除] 已刪除 {deleted_logs} 筆 log、{deleted_jobs} 個過期 job（{LOG_RETENTION_DAYS} 天前）"
        )
    finally:
        await db.close()


def _seconds_until_next_monday_9am() -> float:
    """計算距離下一個星期一 09:00（本地時區 UTC+8）的秒數。"""
    now = datetime.now(timezone.utc)
    # 換算為 UTC+8
    now_local = now + timedelta(hours=8)
    days_until_monday = (7 - now_local.weekday()) % 7  # weekday(): Mon=0
    if days_until_monday == 0 and now_local.hour >= 9:
        days_until_monday = 7  # 今天已過 09:00，等下週一
    next_monday = now_local.replace(hour=9, minute=0, second=0, microsecond=0) + timedelta(days=days_until_monday)
    delta = next_monday - now_local
    return max(delta.total_seconds(), 1.0)


async def start_log_cleaner() -> None:
    """背景排程：每週一 09:00 執行一次 log 清除。"""
    logger.info("[排程] Log 清除排程已啟動")
    while True:
        wait_secs = _seconds_until_next_monday_9am()
        next_run = datetime.now(timezone.utc) + timedelta(seconds=wait_secs)
        logger.info(f"[排程] 下次 log 清除時間：{next_run.strftime('%Y-%m-%d %H:%M UTC')}（等待 {wait_secs/3600:.1f} 小時）")
        await asyncio.sleep(wait_secs)
        try:
            await _cleanup_old_logs()
        except Exception as e:
            logger.error(f"[排程] Log 清除失敗：{e}")
