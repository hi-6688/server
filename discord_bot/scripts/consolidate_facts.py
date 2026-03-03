"""
事實合併腳本 (Facts Consolidation)
用 Gemini 分析每個使用者的所有事實，合併重複/矛盾的條目。
流程：
1. 按 user_id 分組讀取所有 facts
2. 將每組 facts 丟給 Gemini 分析，要求合併精簡
3. 清空舊 facts，寫入新的精簡版
"""
import asyncio
import os
import sys
import json
import asyncpg
from dotenv import load_dotenv

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def consolidate():
    if not DATABASE_URL or not GEMINI_API_KEY:
        print("❌ 缺少環境變數")
        return

    from google import genai
    from google.genai import types
    from utils.memory_manager import MemoryManager

    client = genai.Client(api_key=GEMINI_API_KEY)
    manager = MemoryManager(DATABASE_URL, GEMINI_API_KEY)
    await manager.init_pool(min_size=1, max_size=3)

    conn = await asyncpg.connect(DATABASE_URL)

    print("=" * 60)
    print("🧠 事實合併開始 (AI Consolidation)")
    print("=" * 60)

    # 1. 按 user_id 分組
    users = await conn.fetch("""
        SELECT DISTINCT user_id FROM facts ORDER BY user_id
    """)

    for user_row in users:
        user_id = user_row['user_id']
        facts = await conn.fetch("""
            SELECT id, fact FROM facts WHERE user_id = $1 ORDER BY id
        """, user_id)

        fact_list = [f"#{r['id']}: {r['fact']}" for r in facts]
        fact_ids = [r['id'] for r in facts]

        if len(facts) <= 1:
            print(f"\n👤 {user_id}: 只有 {len(facts)} 筆，跳過")
            continue

        print(f"\n👤 {user_id}: {len(facts)} 筆事實，開始分析...")
        for f in fact_list:
            print(f"  原始: {f}")

        # 2. 讓 Gemini 合併
        prompt = f"""
你是一個資料庫管理員。以下是關於 Discord 使用者 "{user_id}" 的所有事實記錄。
它們可能包含重複、矛盾、或過時的資訊。

請合併成精簡的版本，規則：
1. 合併語意相同的條目（例如「外號白貓」和「暱稱是白貓」合併為一條）
2. 若有矛盾（例如「是男生」vs「是女生」），保留最新的那筆（ID 較大的）
3. 每條事實用 [Data] 或 [Impression] 開頭
   - [Data] = 客觀資料（名字、關係、身分）
   - [Impression] = 主觀印象（個性、習慣、喜好）
4. 回傳 JSON 陣列，每個元素是一條精簡後的事實字串
5. 保留重要細節，不要過度簡化

原始事實：
{chr(10).join(fact_list)}

回傳格式：
["[Data] 合併後的事實1", "[Impression] 合併後的事實2", ...]
"""

        try:
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )

            new_facts = json.loads(response.text)
            print(f"\n  📝 合併結果 ({len(facts)} → {len(new_facts)}):")
            for nf in new_facts:
                print(f"    ✨ {nf}")

            # 3. 清空舊的，寫入新的
            await conn.execute(
                "DELETE FROM facts WHERE user_id = $1",
                user_id
            )
            print(f"  🗑️ 已清除 {len(facts)} 筆舊事實")

            for nf in new_facts:
                vector = await manager.get_embedding(f"{user_id}: {nf}")
                embedding_str = str(vector) if vector else None
                await conn.execute(
                    "INSERT INTO facts (user_id, fact, embedding) VALUES ($1, $2, $3)",
                    user_id, nf, embedding_str
                )
            print(f"  ✅ 已寫入 {len(new_facts)} 筆新事實")

        except Exception as e:
            print(f"  ❌ 合併失敗: {e}")

    # 最終統計
    total = await conn.fetchval("SELECT COUNT(*) FROM facts")
    no_emb = await conn.fetchval("SELECT COUNT(*) FROM facts WHERE embedding IS NULL")
    print(f"\n{'='*60}")
    print(f"📊 合併後統計: {total} 筆事實, {no_emb} 筆缺 Embedding")
    print(f"✅ 合併完成！")

    await conn.close()
    await manager.close_pool()

if __name__ == "__main__":
    asyncio.run(consolidate())
