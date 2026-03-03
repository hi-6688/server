"""
資料庫清理腳本 (Database Cleanup)
執行項目：
1. 刪除測試資料 (TEST_USER_TAGGING, TestUser, test_user)
2. 合併重複事實 (facts dedup)
3. 為所有缺少 Embedding 的 facts 補上 Embedding
"""
import asyncio
import os
import sys
import asyncpg
import json
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def cleanup():
    if not DATABASE_URL or not GEMINI_API_KEY:
        print("❌ 缺少環境變數")
        return

    from utils.memory_manager import MemoryManager
    manager = MemoryManager(DATABASE_URL, GEMINI_API_KEY)
    
    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 60)
    print("🧹 資料庫清理開始")
    print("=" * 60)

    # ==========================================
    # 1. 刪除測試資料
    # ==========================================
    print("\n🗑️ [1] 清除測試資料...")
    
    # memories 表
    test_users = ['TEST_USER_TAGGING', 'TestUser', 'test_user_tagging']
    for tu in test_users:
        cnt = await conn.fetchval("SELECT COUNT(*) FROM memories WHERE user_name = $1", tu)
        if cnt > 0:
            await conn.execute("DELETE FROM memories WHERE user_name = $1", tu)
            print(f"  ✅ 刪除 memories: {tu} ({cnt} 筆)")

    # facts 表
    cnt = await conn.fetchval("SELECT COUNT(*) FROM facts WHERE user_id = 'test_user'")
    if cnt > 0:
        await conn.execute("DELETE FROM facts WHERE user_id = 'test_user'")
        print(f"  ✅ 刪除 facts: test_user ({cnt} 筆)")

    # ==========================================
    # 2. 合併重複/矛盾事實
    # ==========================================
    print("\n🔄 [2] 清理重複/矛盾事實...")
    
    # 找出完全相同的事實
    dupes = await conn.fetch("""
        SELECT user_id, fact, COUNT(*) as cnt
        FROM facts
        GROUP BY user_id, fact
        HAVING COUNT(*) > 1
    """)
    for d in dupes:
        # 保留最新的一筆
        await conn.execute("""
            DELETE FROM facts 
            WHERE user_id = $1 AND fact = $2 
            AND id NOT IN (
                SELECT id FROM facts 
                WHERE user_id = $1 AND fact = $2 
                ORDER BY id DESC LIMIT 1
            )
        """, d['user_id'], d['fact'])
        print(f"  ✅ 去重: {d['user_id']} - {d['fact'][:40]}... (刪除 {d['cnt']-1} 筆重複)")

    # 特定已知的矛盾/過時事實清理
    # piggy0326: 性別矛盾 (保留 #51 不喜歡被認定性別 + #52 是女性)
    # moyin0907: 兄弟/兄妹矛盾 (#55 #56 #74 重複)
    
    # 刪除語意重複的 facts (同一個使用者，內容幾乎一樣)
    # csr.0722_31098: #41, #42, #43, #44 都在說「白貓/本」的名字
    semantic_dupes = [
        # csr.0722_31098 暱稱重複 (保留 #24 最完整的)
        (42, "csr.0722_31098", "小煌的狗的暱稱是「白貓」"),
        (43, "csr.0722_31098", "外號叫「白貓」"),
        (44, "csr.0722_31098", "本名叫做「本」，是阿基的狗"),
        # moyin0907 兄弟關係重複 (保留 #53 和 #74)
        (55, "moyin0907", "魔 是 豬豬 的哥哥"),
        (56, "moyin0907", "魔 (moyin0907) 和 豬豬豬豬 (piggy0326) 是兄弟關係。"),
        # hi6688 重複 (保留 #64)
        (62, "hi6688", "是人類"),
        (63, "hi6688", "人類"),
        # apexdieder 重複 (保留 #59)
        (61, "apexdieder", "稱呼 HiHi 為「女兒」"),
    ]
    
    for fact_id, user_id, fact_text in semantic_dupes:
        exists = await conn.fetchval("SELECT 1 FROM facts WHERE id = $1", fact_id)
        if exists:
            await conn.execute("DELETE FROM facts WHERE id = $1", fact_id)
            print(f"  ✅ 語意去重: #{fact_id} {user_id} - {fact_text[:40]}")

    # ==========================================
    # 3. 為所有 facts 補上 Embedding
    # ==========================================
    print("\n🧬 [3] 為 facts 補上 Embedding...")
    
    rows = await conn.fetch("""
        SELECT id, user_id, fact FROM facts WHERE embedding IS NULL
    """)
    print(f"  需要補 Embedding: {len(rows)} 筆")
    
    success = 0
    for r in rows:
        try:
            vector = await manager.get_embedding(f"{r['user_id']}: {r['fact']}")
            if vector:
                await conn.execute(
                    "UPDATE facts SET embedding = $1 WHERE id = $2",
                    str(vector), r['id']
                )
                success += 1
                print(f"  ✅ #{r['id']} {r['user_id']}: {r['fact'][:30]}...")
        except Exception as e:
            print(f"  ❌ #{r['id']} 失敗: {e}")
    
    print(f"\n  📊 Embedding 補齊: {success}/{len(rows)} 成功")

    # ==========================================
    # 4. 最終統計
    # ==========================================
    print("\n" + "=" * 60)
    print("📊 清理後統計:")
    for table in ['memories', 'facts', 'chat_history', 'knowledge', 'image_memory']:
        cnt = await conn.fetchval(f"SELECT COUNT(*) FROM {table}")
        print(f"  - {table}: {cnt} 筆")
    
    no_emb = await conn.fetchval("SELECT COUNT(*) FROM facts WHERE embedding IS NULL")
    print(f"\n  - facts 缺少 Embedding: {no_emb} 筆")

    await conn.close()
    print("\n✅ 清理完成！")

if __name__ == "__main__":
    asyncio.run(cleanup())
