
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")
DB_URL = os.getenv("DATABASE_URL")

async def init_db():
    print(f"Connecting to {DB_URL.split('@')[1]}...")
    conn = await asyncpg.connect(DB_URL)
    try:
        print("Creating table 'knowledge'...")
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS knowledge (
                term TEXT PRIMARY KEY,
                definition TEXT NOT NULL,
                category TEXT,
                embedding vector(768),
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # Create Update/Search Index (Optional, for performance)
        # await conn.execute("CREATE INDEX ON knowledge USING hnsw (embedding vector_cosine_ops);")
        
        print("✅ Table 'knowledge' created successfully.")
    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(init_db())
