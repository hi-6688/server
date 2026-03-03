
import asyncio
import os
import sys
from dotenv import load_dotenv

# Ensure we can import from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.memory_manager import MemoryManager

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def test_memory_tagging():
    if not DATABASE_URL or not GEMINI_API_KEY:
        print("❌ Missing ENV vars.")
        return

    manager = MemoryManager(DATABASE_URL, GEMINI_API_KEY)
    
    test_content = "HiHi 覺得 Python 寫起來比 C++ 舒服多了，雖然效能差一點，但開發速度很快。"
    user_name = "TEST_USER_TAGGING"
    
    print(f"🔬 Testing AI Tagging with content: '{test_content}'")
    
    # 1. Add Memory (Should trigger _analyze_content)
    await manager.add_memory(user_name, test_content, importance=5, type="test", metadata={"source": "script"})
    
    # 2. Verify Metadata from DB
    import asyncpg
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow("SELECT metadata FROM memories WHERE user_name=$1 AND content=$2 ORDER BY id DESC LIMIT 1", user_name, test_content)
    await conn.close()
    
    if row and row['metadata']:
        meta = row['metadata'] # asyncpg returns specific type, might need json.loads if string, but usually returns dict for jsonb
        import json
        if isinstance(meta, str):
            meta = json.loads(meta)
            
        print("\n✅ Metadata Retrieved:")
        print(json.dumps(meta, indent=2, ensure_ascii=False))
        
        if "topics" in meta and "sentiment" in meta:
            print("\n🎉 SUCCESS: AI Tagging works!")
        else:
            print("\n⚠️ WARNING: Metadata missing expected fields.")
    else:
        print("\n❌ FAILED: No metadata found.")

if __name__ == "__main__":
    asyncio.run(test_memory_tagging())
