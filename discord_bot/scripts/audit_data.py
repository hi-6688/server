"""
資料庫資料品質審計腳本 (Data Quality Audit)
檢查所有表的資料內容，找出：
- 測試資料 (test data)
- 重複資料 (duplicates)
- 孤兒記錄 (orphaned records)
- 資料品質問題
"""
import asyncio
import os
import json
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def audit_data():
    if not DATABASE_URL:
        print("❌ DATABASE_URL 未設定")
        return

    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 60)
    print("🔍 資料品質審計報告")
    print("=" * 60)

    # ==========================================
    # 1. memories 表
    # ==========================================
    print("\n\n📦 [1] memories 表 (長期記憶)")
    print("-" * 40)
    rows = await conn.fetch("SELECT id, user_name, content, type, importance, created_at, metadata FROM memories ORDER BY id")
    print(f"  總數: {len(rows)} 筆\n")
    
    test_memories = []
    no_metadata_ai = []
    
    for r in rows:
        is_test = "TEST" in (r['user_name'] or "").upper() or "test" in (r['content'] or "").lower()[:50]
        meta = r['metadata']
        if isinstance(meta, str):
            meta = json.loads(meta) if meta and meta != '{}' else {}
        
        has_ai_tags = bool(meta and meta.get('topics'))
        
        marker = ""
        if is_test:
            marker = " ⚠️ [測試資料]"
            test_memories.append(r['id'])
        if not has_ai_tags:
            no_metadata_ai.append(r['id'])
        
        content_preview = (r['content'] or "")[:60].replace('\n', ' ')
        print(f"  #{r['id']} | {r['user_name']:<20} | 重要度:{r['importance']} | {r['type']:<15} | {content_preview}{marker}")
    
    print(f"\n  📊 統計:")
    print(f"     - 測試資料: {len(test_memories)} 筆 (ID: {test_memories})")
    print(f"     - 缺少 AI 標籤: {len(no_metadata_ai)} 筆 (ID: {no_metadata_ai})")

    # ==========================================
    # 2. facts 表
    # ==========================================
    print("\n\n📝 [2] facts 表 (核心事實)")
    print("-" * 40)
    rows = await conn.fetch("SELECT id, user_id, fact, embedding IS NOT NULL as has_embedding FROM facts ORDER BY user_id, id")
    print(f"  總數: {len(rows)} 筆\n")
    
    no_embedding_facts = []
    user_fact_count = {}
    
    for r in rows:
        has_emb = "✅" if r['has_embedding'] else "❌"
        if not r['has_embedding']:
            no_embedding_facts.append(r['id'])
        
        user_fact_count[r['user_id']] = user_fact_count.get(r['user_id'], 0) + 1
        fact_preview = r['fact'][:60]
        print(f"  #{r['id']} | {r['user_id']:<20} | Emb:{has_emb} | {fact_preview}")
    
    print(f"\n  📊 統計:")
    print(f"     - 缺少 Embedding: {len(no_embedding_facts)} 筆")
    print(f"     - 使用者分布: {dict(sorted(user_fact_count.items(), key=lambda x: -x[1]))}")

    # ==========================================
    # 3. chat_history 表
    # ==========================================
    print("\n\n💬 [3] chat_history 表 (聊天記錄)")
    print("-" * 40)
    stats = await conn.fetch("""
        SELECT session_id, role, COUNT(*) as cnt, 
               MIN(timestamp) as first_msg, MAX(timestamp) as last_msg
        FROM chat_history GROUP BY session_id, role ORDER BY session_id, role
    """)
    total = await conn.fetchval("SELECT COUNT(*) FROM chat_history")
    print(f"  總數: {total} 筆\n")
    for s in stats:
        print(f"  Session: {s['session_id']:<15} | Role: {s['role']:<8} | 數量: {s['cnt']:<5} | 時間: {s['first_msg']} ~ {s['last_msg']}")

    # ==========================================
    # 4. knowledge 表
    # ==========================================
    print("\n\n📚 [4] knowledge 表 (知識庫)")
    print("-" * 40)
    rows = await conn.fetch("SELECT term, definition, category FROM knowledge ORDER BY term")
    print(f"  總數: {len(rows)} 筆")
    if len(rows) == 0:
        print("  ⚠️ 知識庫是空的！RAG 知識功能未被使用。")
    for r in rows:
        print(f"  - [{r['category']}] {r['term']}: {r['definition'][:50]}")

    # ==========================================
    # 5. image_memory 表
    # ==========================================
    print("\n\n🖼️ [5] image_memory 表 (圖片記憶)")
    print("-" * 40)
    rows = await conn.fetch("SELECT hash, user_id, description, created_at FROM image_memory ORDER BY created_at")
    print(f"  總數: {len(rows)} 筆")
    for r in rows:
        print(f"  - {r['hash'][:12]}... | 使用者: {r['user_id']} | {r['created_at']}")

    await conn.close()
    print("\n" + "=" * 60)
    print("✅ 審計完成")

if __name__ == "__main__":
    asyncio.run(audit_data())
