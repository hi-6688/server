
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load .env
load_dotenv("/home/terraria/servers/.env")

DATABASE_URL = os.getenv("DATABASE_URL")

async def test_connection():
    print(f"Connecting to: {DATABASE_URL}")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Success! Connected to Azure PostgreSQL.")
        
        # Test query
        version = await conn.fetchval("SELECT version()")
        print(f"Database/Version: {version}")
        
        await conn.close()
        print("Connection closed.")
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_connection())
