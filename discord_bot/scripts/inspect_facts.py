
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")
DB_URL = os.getenv("DATABASE_URL")

async def inspect():
    if not DB_URL:
        print("❌ DATABASE_URL not set")
        return
    try:
        conn = await asyncpg.connect(DB_URL)
        print("🔍 Inspecting Facts Table...")
        
        # Fetch all facts ordered by user
        rows = await conn.fetch("SELECT user_id, fact FROM facts ORDER BY user_id")
        
        current_user = None
        for r in rows:
            if r['user_id'] != current_user:
                print(f"\n👤 User: {r['user_id']}")
                current_user = r['user_id']
            print(f"   - {r['fact']}")
            
        await conn.close()
    except Exception as e:
        print(f"❌ DB Error: {e}")

if __name__ == "__main__":
    asyncio.run(inspect())
