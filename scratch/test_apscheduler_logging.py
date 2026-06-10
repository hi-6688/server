import asyncio
import os
import logging
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# 設置 logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger("apscheduler_test")

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.date import DateTrigger

async def tick(message):
    print(f"⏰ [Job Executed] Time: {datetime.now()}, Message: {message}")

async def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL not found!")
        return
    cleaned_db_url = db_url.replace("postgres://", "postgresql+asyncpg://").replace("?sslmode=require", "")
    
    engine = create_async_engine(cleaned_db_url)
    data_store = SQLAlchemyDataStore(engine)
    
    # 清理之前的舊排程以防干擾
    # SQLAlchemyDataStore 會在 `apscheduler_schedules` 表中存儲
    
    async with AsyncScheduler(data_store) as scheduler:
        wakeup_time = datetime.now() + timedelta(seconds=2)
        print(f"Adding schedule for {wakeup_time}")
        await scheduler.add_schedule(
            tick,
            DateTrigger(run_time=wakeup_time),
            id="test_logging_heartbeat",
            args=["Hello with Logging!"],
            conflict_policy="replace"
        )
        
        scheduler_task = asyncio.create_task(scheduler.run_until_stopped())
        await asyncio.sleep(5)
        scheduler_task.cancel()
        try:
            await scheduler_task
        except asyncio.CancelledError:
            pass
            
    await engine.dispose()

if __name__ == "__main__":
    asyncio.run(main())
