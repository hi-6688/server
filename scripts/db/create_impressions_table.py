import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")

async def main():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("缺少 DATABASE_URL")
        return
        
    conn = await asyncpg.connect(db_url)
    try:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS user_impressions (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                user_name TEXT NOT NULL,
                impression TEXT NOT NULL,
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
            CREATE UNIQUE INDEX IF NOT EXISTS idx_user_impressions_user_id ON user_impressions(user_id);
        """)
        print("成功建立 user_impressions 資料表！")
    except Exception as e:
        print(f"建立資料表錯誤: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(main())
