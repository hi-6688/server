import asyncio
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("apscheduler_misfire")

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.date import DateTrigger

misfire_triggered = False

async def tick(message):
    global misfire_triggered
    misfire_triggered = True
    print(f"⏰ [Job Executed] Time: {datetime.now()}, Message: {message}")

async def run_stage_1(db_url):
    print("\n--- 🎬 [Stage 1] 模擬排程投遞與停機 ---")
    engine = create_async_engine(db_url)
    data_store = SQLAlchemyDataStore(engine)
    
    async with AsyncScheduler(data_store) as scheduler:
        # 安排一個 3 秒後執行的任務
        wakeup_time = datetime.now() + timedelta(seconds=3)
        print(f"📅 安排一個 3 秒後的主動甦醒心跳：{wakeup_time}")
        
        await scheduler.add_schedule(
            tick,
            DateTrigger(run_time=wakeup_time),
            id="hihi_misfire_test_logging",
            args=["Stage 1 補償心跳發射！"],
            conflict_policy="replace"
        )
        print("💾 心跳已持久化至 Postgres。現在立刻關閉 Scheduler 模擬崩潰！")
    
    await engine.dispose()

async def run_stage_2(db_url):
    print("\n--- 🎬 [Stage 2] 模擬重啟並觸發 misfire 補償 ---")
    engine = create_async_engine(db_url)
    data_store = SQLAlchemyDataStore(engine)
    
    async with AsyncScheduler(data_store) as scheduler:
        print("🚀 重啟排程器...")
        scheduler_task = asyncio.create_task(scheduler.run_until_stopped())
        
        await asyncio.sleep(5)
        
        print("🧹 關閉排程器...")
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
            
    await engine.dispose()

async def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found!")
        return
    cleaned_db_url = db_url.replace("postgres://", "postgresql+asyncpg://").replace("?sslmode=require", "")
    
    # 清理舊的以防干擾
    await run_stage_1(cleaned_db_url)
    print("\n⌛ 停機中... 等待 5 秒讓任務過期...")
    await asyncio.sleep(5)
    await run_stage_2(cleaned_db_url)
    
    if misfire_triggered:
        print("\n🎉 [SUCCESS] Misfire 任務已成功補發！")
    else:
        print("\n❌ [FAILURE] Misfire 任務沒有被補發！")

if __name__ == "__main__":
    asyncio.run(main())
