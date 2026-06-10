# -*- coding: utf-8 -*-
from datetime import datetime, timedelta, timezone

async def execute_sleep_scheduling(cog_instance, seconds: int, intent: str) -> str:
    """
    執行大腦生理休眠與鬧鐘的排程與 PostgreSQL 持久化。
    """
    # 呼叫新版排程方法投遞 Job，APScheduler 會自動將排程持久化至資料庫
    await cog_instance.schedule_next_sleep(seconds, intent)
    return f"✅ 已成功為您排程下一次生理休眠 {seconds} 秒，狀態已由 APScheduler 持久化至 PostgreSQL 資料庫。"

