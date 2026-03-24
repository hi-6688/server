from dotenv import load_dotenv
import asyncio
import os
import sys

# 把 utils 加到 path 以便載入
sys.path.append("/home/terraria/servers/discord_bot")
from utils.memory_manager import MemoryManager

load_dotenv("/home/terraria/servers/.env")

async def test():
    db_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("GEMINI_API_KEY")
    mm = MemoryManager(db_url, api_key)
    await mm.init_pool(1, 2)
    
    await mm.update_user_impression("123", "TestUser", "這個測試使用者很有趣。")
    res = await mm.get_user_impression("123")
    print(f"Result: {res}")
    
    await mm.close_pool()

asyncio.run(test())
