
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")
DB_URL = os.getenv("DATABASE_URL")

async def init_db():
    if not DB_URL: return
    conn = await asyncpg.connect(DB_URL)
    try:
        print("🔨 Creating image_memory table...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS image_memory (
                hash TEXT PRIMARY KEY,
                user_id TEXT,
                description TEXT, /* Optional: AI generated caption */
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("✅ Table created successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_db())
