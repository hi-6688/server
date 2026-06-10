import asyncio
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv
from sqlalchemy.ext.asyncio import create_async_engine

# 載入環境變數
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

try:
    from apscheduler import AsyncScheduler
    from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
    from apscheduler.triggers.date import DateTrigger
    print("✅ APScheduler 4.0 classes imported successfully!")
except Exception as e:
    print("❌ Failed to import APScheduler 4.0:", e)
    import sys
    sys.exit(1)

misfire_triggered = False

async def tick(message):
    global misfire_triggered
    misfire_triggered = True
    print(f"⏰ [Job Executed] Time: {datetime.now()}, Message: {message}")

async def run_stage_1(db_url):
    """
    第一階段：安排一個未來 3 秒執行的任務，然後立刻關閉（模擬服務器寫入排程後立刻掛掉）。
    """
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
            id="hihi_misfire_test",
            args=["Stage 1 補償心跳發射！"],
            conflict_policy="replace"
        )
        print("💾 心跳已持久化至 Postgres。現在立刻關閉 Scheduler 模擬崩潰！")
    
    await engine.dispose()

async def run_stage_2(db_url):
    """
    第二階段：等待 5 秒（讓第一階段安排的任務在停機期間過期），然後重啟排程器。
    排程器應該會因為 misfire_grace_time 補發該心跳！
    """
    print("\n--- 🎬 [Stage 2] 模擬重啟並觸發 misfire 補償 ---")
    engine = create_async_engine(db_url)
    data_store = SQLAlchemyDataStore(engine)
    
    async with AsyncScheduler(data_store) as scheduler:
        print("🚀 重啟排程器。若在停機期間過期，且在 misfire 寬限內，此處應自動補發執行...")
        scheduler_task = asyncio.create_task(scheduler.run_until_stopped())
        
        # 等待 4 秒，看是否有觸發補償任務
        await asyncio.sleep(4)
        
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
        print("❌ DATABASE_URL not found in environment!")
        return
        
    cleaned_db_url = db_url.replace("postgres://", "postgresql+asyncpg://").replace("?sslmode=require", "")
    print(f"🔌 Testing PostgreSQL Connection URL: {cleaned_db_url.split('@')[-1]}")
    
    # 1. 執行第一階段（排程落盤）
    await run_stage_1(cleaned_db_url)
    
    # 2. 等待 5 秒讓時間過期
    print("\n⌛ 停機中... 等待 5 秒讓任務過期...")
    await asyncio.sleep(5)
    
    # 3. 執行第二階段（重啟補發）
    await run_stage_2(cleaned_db_url)
    
    if misfire_triggered:
        print("\n🎉 [SUCCESS] Misfire 補償甦醒任務成功觸發！")
    else:
        print("\n❌ [FAILURE] Misfire 任務沒有被補發執行。")

if __name__ == "__main__":
    asyncio.run(main())
