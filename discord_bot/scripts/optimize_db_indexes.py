"""
資料庫索引優化腳本 (Database Index Optimization)
建立所有必要的索引：
1. chat_history(session_id, timestamp DESC) — 加速歷史查詢
2. knowledge(embedding) HNSW — 加速知識語意搜尋
3. memories(embedding) HNSW — 加速記憶語意搜尋
4. facts(user_id) — 加速事實查詢
"""
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

INDEXES = [
    {
        "name": "idx_chat_history_session_time",
        "sql": "CREATE INDEX IF NOT EXISTS idx_chat_history_session_time ON chat_history (session_id, timestamp DESC);",
        "desc": "chat_history 按頻道+時間排序索引"
    },
    {
        "name": "idx_knowledge_embedding_hnsw",
        "sql": "CREATE INDEX IF NOT EXISTS idx_knowledge_embedding_hnsw ON knowledge USING hnsw (embedding vector_cosine_ops);",
        "desc": "knowledge 向量 HNSW 索引"
    },
    {
        "name": "idx_memories_embedding_hnsw",
        "sql": "CREATE INDEX IF NOT EXISTS idx_memories_embedding_hnsw ON memories USING hnsw (embedding vector_cosine_ops);",
        "desc": "memories 向量 HNSW 索引"
    },
    {
        "name": "idx_facts_user_id",
        "sql": "CREATE INDEX IF NOT EXISTS idx_facts_user_id ON facts (user_id);",
        "desc": "facts 按使用者查詢索引"
    },
]

async def optimize():
    if not DATABASE_URL:
        print("❌ DATABASE_URL 未設定。")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        for idx in INDEXES:
            print(f"🔧 建立索引: {idx['desc']}...")
            try:
                await conn.execute(idx["sql"])
                print(f"  ✅ {idx['name']} 建立成功！")
            except Exception as e:
                print(f"  ⚠️ {idx['name']} 失敗: {e}")
        
        # 驗證所有索引
        print("\n📇 目前所有索引：")
        rows = await conn.fetch("""
            SELECT indexname, tablename FROM pg_indexes 
            WHERE schemaname = 'public' ORDER BY tablename, indexname
        """)
        for r in rows:
            print(f"  - [{r['tablename']}] {r['indexname']}")
            
    finally:
        await conn.close()
    
    print("\n✅ 索引優化完成！")

if __name__ == "__main__":
    asyncio.run(optimize())
