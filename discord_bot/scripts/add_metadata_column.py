
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")
DB_URL = os.getenv("DATABASE_URL")

async def update_schema():
    if not DB_URL: return
    conn = await asyncpg.connect(DB_URL)
    try:
        print("🔨 Altering memories table...")
        await conn.execute("""
            ALTER TABLE memories 
            ADD COLUMN IF NOT EXISTS metadata JSONB DEFAULT '{}'::jsonb;
        """)
        print("✅ Column 'metadata' added successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(update_schema())
