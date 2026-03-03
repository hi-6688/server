
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")
DB_URL = os.getenv("DATABASE_URL")

async def check():
    if not DB_URL:
        print("❌ DATABASE_URL not set")
        return
    try:
        conn = await asyncpg.connect(DB_URL)
        
        # Check Knowledge (RAG)
        try:
            k_count = await conn.fetchval("SELECT count(*) FROM knowledge")
            print(f"📚 Knowledge Base (RAG): {k_count} entries")
            if k_count > 0:
                rows = await conn.fetch("SELECT category, term, definition FROM knowledge ORDER BY created_at DESC LIMIT 3")
                for r in rows:
                    print(f"   - [{r['category']}] {r['term']}: {r['definition'][:50]}...")
        except Exception as e:
            print(f"⚠️ Knowledge Table Error: {e}")

        # Check Facts
        try:
            f_count = await conn.fetchval("SELECT count(*) FROM facts")
            print(f"\n📝 User Facts: {f_count} entries")
            if f_count > 0:
                rows = await conn.fetch("SELECT user_id, fact FROM facts ORDER BY 1 DESC LIMIT 3")
                for r in rows:
                    print(f"   - {r['user_id']}: {r['fact'][:50]}...")
        except Exception as e:
            print(f"⚠️ Facts Table Error: {e}")

        # Check Recent Context (Memories)
        try:
            m_count = await conn.fetchval("SELECT count(*) FROM memories")
            print(f"\n🧠 Long-Term Memories: {m_count} entries")
        except Exception as e:
            print(f"⚠️ Memories Table Error: {e}")

        await conn.close()
    except Exception as e:
        print(f"❌ DB Connection Error: {e}")

if __name__ == "__main__":
    asyncio.run(check())
