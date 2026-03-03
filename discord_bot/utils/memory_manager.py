"""
HiHi 記憶管理器 v3.0 (Memory Manager)
PostgreSQL 全面優化版

功能：
- 連線池 (Connection Pool) — 效能提升 10 倍
- 混合搜尋 (Hybrid Search) — Vector + Full-Text + RRF 排序
- AI 自動標籤 (Auto-Tagging) — Gemini 結構化分析
- Facts 語意搜尋 — Embedding-based fact retrieval
"""

import os
import asyncio
import asyncpg
from google import genai
from google.genai import types
from typing import List, Dict, Any, Optional
import datetime
import json

class MemoryManager:
    def __init__(self, db_url: str, google_api_key: str):
        self.db_url = db_url
        self.client = genai.Client(api_key=google_api_key)
        self.embedding_model = "gemini-embedding-001"
        self.tagging_model = "gemini-3-flash-preview"
        # 連線池 (初始化時為 None，需要呼叫 init_pool)
        self.pool: Optional[asyncpg.Pool] = None

    # =========================================================================
    # 🔌 連線池管理 (Connection Pool)
    # =========================================================================

    async def init_pool(self, min_size: int = 2, max_size: int = 10):
        """
        初始化連線池。應在 Bot 啟動時呼叫。
        min_size: 最小保持連線數
        max_size: 最大連線數
        """
        if self.pool is not None:
            return  # 已初始化

        self.pool = await asyncpg.create_pool(
            self.db_url,
            min_size=min_size,
            max_size=max_size,
            command_timeout=30
        )
        print(f"🔌 [DB] 連線池已建立 (min={min_size}, max={max_size})")

    async def close_pool(self):
        """
        關閉連線池。應在 Bot 關閉時呼叫。
        """
        if self.pool:
            await self.pool.close()
            self.pool = None
            print("🔌 [DB] 連線池已關閉")

    async def _get_conn(self):
        """
        取得連線。優先使用連線池，若未初始化則 fallback 到單次連線。
        """
        if self.pool:
            return self.pool
        # Fallback: 單次連線 (相容舊版呼叫)
        return await asyncpg.connect(self.db_url)

    # =========================================================================
    # 🧬 Embedding 生成
    # =========================================================================

    async def get_embedding(self, text: str) -> List[float]:
        """
        將文字轉換為 768 維向量 (Gemini Embedding)。
        """
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_DOCUMENT",
                    output_dimensionality=768
                )
            )
            return response.embeddings[0].values
        except Exception as e:
            print(f"❌ Embedding 錯誤: {e}")
            return []

    # =========================================================================
    # 🧠 長期記憶 (Memories)
    # =========================================================================

    async def add_memory(self, user_name: str, content: str, importance: int = 1, type: str = "observation", metadata: Dict[str, Any] = None):
        """
        儲存新記憶到 PostgreSQL (memories 表)。
        自動進行 AI 標籤分析 + 向量嵌入。
        """
        # 1. AI 自動標籤
        try:
            ai_meta = await self._analyze_content(content)
            if ai_meta:
                if metadata is None:
                    metadata = {}
                metadata.update(ai_meta)
                print(f"🧠 [Memory] AI 標籤: {ai_meta}")
        except Exception as e:
            print(f"⚠️ AI 標籤失敗 (不影響儲存): {e}")

        # 2. 生成 Embedding
        vector = await self.get_embedding(content)
        if not vector:
            print("❌ 無法生成 Embedding，跳過儲存。")
            return

        # 3. 寫入資料庫
        meta_json = json.dumps(metadata, ensure_ascii=False) if metadata else "{}"
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO memories (user_name, content, importance, type, embedding, metadata)
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, user_name, content, importance, type, str(vector), meta_json)
                print(f"✅ 記憶已儲存: {user_name} - {content[:30]}... (重要度: {importance})")
            except Exception as e:
                print(f"❌ 記憶寫入錯誤: {e}")

    async def _analyze_content(self, content: str) -> Optional[Dict[str, Any]]:
        """
        使用 Gemini Flash 分析內容，回傳結構化 metadata。
        """
        try:
            prompt = f"""
            分析以下記憶內容，萃取結構化 metadata (JSON 格式)。
            內容: "{content}"
            
            JSON Schema:
            {{
                "topics": ["主題1", "主題2"],
                "entities": ["人物/物品1", "人物/物品2"],
                "sentiment": "positive" | "negative" | "neutral",
                "category": "FACT" | "OPINION" | "EVENT" | "KNOWLEDGE",
                "keywords": ["關鍵字1", "關鍵字2"]
            }}
            
            只回傳 JSON 物件。
            """

            response = self.client.models.generate_content(
                model=self.tagging_model,
                contents=prompt,
                config=types.GenerateContentConfig(response_mime_type="application/json")
            )
            return json.loads(response.text)
        except Exception as e:
            print(f"⚠️ 內容分析錯誤: {e}")
            return None

    async def search_memory(self, query: str, limit: int = 3) -> List[Dict[str, Any]]:
        """
        混合搜尋 (Hybrid Search)：
        1. Vector Search (語意相似度)
        2. Full-Text Search (關鍵字匹配)
        3. RRF (Reciprocal Rank Fusion) 合併排名
        """
        # 生成查詢向量
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=query,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=768
                )
            )
            query_vector = response.embeddings[0].values
        except Exception as e:
            print(f"❌ 查詢 Embedding 錯誤: {e}")
            return []

        async with self.pool.acquire() as conn:
            memories = []
            try:
                # 混合搜尋 SQL (RRF = Reciprocal Rank Fusion)
                # k=60 是 RRF 標準常數
                rows = await conn.fetch("""
                    WITH vector_search AS (
                        SELECT id, content, user_name, importance, created_at, metadata,
                               1 - (embedding <=> $1) as similarity,
                               ROW_NUMBER() OVER (ORDER BY embedding <=> $1) as vector_rank
                        FROM memories
                        ORDER BY embedding <=> $1
                        LIMIT 20
                    ),
                    fts_search AS (
                        SELECT id,
                               ROW_NUMBER() OVER (ORDER BY ts_rank(to_tsvector('simple', content), plainto_tsquery('simple', $2)) DESC) as fts_rank
                        FROM memories
                        WHERE to_tsvector('simple', content) @@ plainto_tsquery('simple', $2)
                        LIMIT 20
                    )
                    SELECT v.content, v.user_name, v.importance, v.created_at, v.metadata, v.similarity,
                           (1.0 / (60 + v.vector_rank)) + COALESCE(1.0 / (60 + f.fts_rank), 0) as rrf_score
                    FROM vector_search v
                    LEFT JOIN fts_search f ON v.id = f.id
                    ORDER BY rrf_score DESC
                    LIMIT $3
                """, str(query_vector), query, limit)

                for row in rows:
                    meta = row['metadata']
                    if isinstance(meta, str):
                        meta = json.loads(meta) if meta else {}
                    memories.append({
                        "content": row['content'],
                        "user_name": row['user_name'],
                        "importance": row['importance'],
                        "created_at": row['created_at'],
                        "metadata": meta if meta else {},
                        "similarity": row['similarity']
                    })
            except Exception as e:
                print(f"❌ 記憶搜尋錯誤: {e}")

        return memories

    # =========================================================================
    # 📝 核心事實 (Facts) — 語意去重版 (Semantic Dedup)
    # =========================================================================

    # 語意去重閾值：若新事實與舊事實的 Embedding 相似度超過此值，視為「同一件事」
    DEDUP_THRESHOLD = 0.85

    async def add_fact(self, user_id: str, fact: str):
        """
        智能新增事實 (Semantic Dedup)：
        1. 生成新事實的 Embedding
        2. 搜尋該使用者的所有舊事實
        3. 若有相似度 > 0.85 的舊事實 → UPDATE（替換舊的）
        4. 若無相似 → INSERT（新增）
        """
        # 1. 生成 Embedding
        vector = await self.get_embedding(f"{user_id}: {fact}")
        if not vector:
            print(f"⚠️ 無法生成 Embedding，改用精確比對")
            # Fallback: 精確比對
            async with self.pool.acquire() as conn:
                exists = await conn.fetchval(
                    "SELECT 1 FROM facts WHERE user_id = $1 AND fact = $2",
                    str(user_id), fact
                )
                if not exists:
                    await conn.execute(
                        "INSERT INTO facts (user_id, fact) VALUES ($1, $2)",
                        str(user_id), fact
                    )
                    print(f"✅ 事實已儲存 (無 Embedding): {user_id} - {fact}")
            return

        embedding_str = str(vector)

        async with self.pool.acquire() as conn:
            try:
                # 2. 搜尋該使用者的相似事實
                similar = await conn.fetchrow("""
                    SELECT id, fact, 1 - (embedding <=> $1) as similarity
                    FROM facts
                    WHERE user_id = $2 AND embedding IS NOT NULL
                    ORDER BY embedding <=> $1
                    LIMIT 1
                """, embedding_str, str(user_id))

                if similar and similar['similarity'] >= self.DEDUP_THRESHOLD:
                    # 3. 找到相似 → UPDATE
                    old_fact = similar['fact']
                    await conn.execute("""
                        UPDATE facts SET fact = $1, embedding = $2, created_at = CURRENT_TIMESTAMP
                        WHERE id = $3
                    """, fact, embedding_str, similar['id'])
                    print(f"🔄 事實已更新: {user_id}")
                    print(f"   舊: {old_fact}")
                    print(f"   新: {fact}")
                    print(f"   相似度: {similar['similarity']:.4f}")
                else:
                    # 4. 沒找到 → INSERT
                    await conn.execute("""
                        INSERT INTO facts (user_id, fact, embedding)
                        VALUES ($1, $2, $3)
                    """, str(user_id), fact, embedding_str)
                    sim_info = f" (最近相似: {similar['similarity']:.4f})" if similar else ""
                    print(f"✅ 事實已儲存: {user_id} - {fact}{sim_info}")

            except Exception as e:
                print(f"❌ 事實寫入錯誤: {e}")

    async def remove_fact(self, user_id: str, fact: str):
        """
        模糊刪除事實 (Fuzzy Delete)：
        先嘗試精確匹配，不行的話用 Embedding 找最相似的來刪。
        """
        async with self.pool.acquire() as conn:
            try:
                # 嘗試 1: 精確匹配
                result = await conn.execute("""
                    DELETE FROM facts WHERE user_id = $1 AND fact = $2
                """, str(user_id), fact)

                # 檢查是否真的刪到了 (asyncpg 的 execute 回傳 "DELETE N")
                deleted_count = int(result.split(" ")[-1])

                if deleted_count > 0:
                    print(f"🗑️ 事實已移除 (精確): {user_id} - {fact}")
                else:
                    # 嘗試 2: 模糊匹配 (Embedding)
                    vector = await self.get_embedding(f"{user_id}: {fact}")
                    if vector:
                        similar = await conn.fetchrow("""
                            SELECT id, fact, 1 - (embedding <=> $1) as similarity
                            FROM facts
                            WHERE user_id = $2 AND embedding IS NOT NULL
                            ORDER BY embedding <=> $1
                            LIMIT 1
                        """, str(vector), str(user_id))

                        if similar and similar['similarity'] >= 0.75:
                            await conn.execute("DELETE FROM facts WHERE id = $1", similar['id'])
                            print(f"🗑️ 事實已移除 (模糊): {user_id}")
                            print(f"   目標: {fact}")
                            print(f"   實際刪除: {similar['fact']}")
                            print(f"   相似度: {similar['similarity']:.4f}")
                        else:
                            print(f"⚠️ 找不到相似事實可刪除: {user_id} - {fact}")
                    else:
                        print(f"⚠️ 無法比對，事實未刪除: {user_id} - {fact}")

            except Exception as e:
                print(f"❌ 事實刪除錯誤: {e}")

    async def get_facts(self, user_id: str) -> List[str]:
        """
        取得特定使用者的所有事實。
        """
        async with self.pool.acquire() as conn:
            try:
                rows = await conn.fetch("""
                    SELECT fact FROM facts WHERE user_id = $1
                """, str(user_id))
                return [row['fact'] for row in rows]
            except Exception as e:
                print(f"❌ 事實查詢錯誤: {e}")
                return []

    async def search_facts_by_topic(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        語意搜尋事實 (跨使用者)。
        例如：「誰喜歡遊戲？」→ 回傳所有相關使用者的事實。
        """
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=query,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=768
                )
            )
            query_vector = response.embeddings[0].values
        except Exception as e:
            print(f"❌ 事實搜尋 Embedding 錯誤: {e}")
            return []

        async with self.pool.acquire() as conn:
            results = []
            try:
                rows = await conn.fetch("""
                    SELECT user_id, fact, 1 - (embedding <=> $1) as similarity
                    FROM facts
                    WHERE embedding IS NOT NULL
                    AND 1 - (embedding <=> $1) > 0.5
                    ORDER BY embedding <=> $1
                    LIMIT $2
                """, str(query_vector), limit)
                for row in rows:
                    results.append({
                        "user_id": row['user_id'],
                        "fact": row['fact'],
                        "similarity": row['similarity']
                    })
            except Exception as e:
                print(f"❌ 事實語意搜尋錯誤: {e}")
            return results

    # =========================================================================
    # 📜 聊天記錄 (Chat History)
    # =========================================================================

    async def log_chat(self, role: str, content: str, session_id: str = "global"):
        """
        記錄聊天訊息 (chat_history 表)。
        """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO chat_history (role, content, session_id)
                    VALUES ($1, $2, $3)
                """, role, content, session_id)
            except Exception as e:
                print(f"❌ 聊天記錄錯誤: {e}")

    async def get_recent_chat_history(self, limit: int = 10) -> List[Dict[str, str]]:
        """
        取得近期聊天記錄 (按時間正序)。
        """
        async with self.pool.acquire() as conn:
            history = []
            try:
                rows = await conn.fetch("""
                    SELECT role, content FROM chat_history
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)
                # 反轉為時間正序
                for row in reversed(rows):
                    history.append({"role": row['role'], "content": row['content']})
            except Exception as e:
                print(f"❌ 聊天記錄查詢錯誤: {e}")
            return history

    # =========================================================================
    # 📚 RAG 知識庫 (Knowledge)
    # =========================================================================

    async def add_knowledge(self, term: str, definition: str, category: str = "General"):
        """
        新增/更新知識條目 (Upsert)。
        自動生成 Embedding 以支援語意搜尋。
        """
        content_to_embed = f"{term}: {definition}"
        vector = await self.get_embedding(content_to_embed)
        if not vector:
            print("❌ 無法生成知識 Embedding。")
            return

        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO knowledge (term, definition, category, embedding)
                    VALUES ($1, $2, $3, $4)
                    ON CONFLICT (term) DO UPDATE
                    SET definition = EXCLUDED.definition,
                        category = EXCLUDED.category,
                        embedding = EXCLUDED.embedding,
                        created_at = CURRENT_TIMESTAMP
                """, term, definition, category, str(vector))
                print(f"📚 知識已儲存: [{category}] {term} -> {definition}")
            except Exception as e:
                print(f"❌ 知識寫入錯誤: {e}")

    async def search_knowledge(self, query: str, limit: int = 3) -> str:
        """
        混合搜尋知識庫：Vector + 關鍵字。
        回傳格式化字串供 System Prompt 注入。
        """
        try:
            response = self.client.models.embed_content(
                model=self.embedding_model,
                contents=query,
                config=types.EmbedContentConfig(
                    task_type="RETRIEVAL_QUERY",
                    output_dimensionality=768
                )
            )
            query_vector = response.embeddings[0].values
        except Exception as e:
            print(f"❌ 知識搜尋 Embedding 錯誤: {e}")
            return ""

        async with self.pool.acquire() as conn:
            results = []
            try:
                rows = await conn.fetch("""
                    SELECT term, definition, category, 1 - (embedding <=> $1) as similarity
                    FROM knowledge
                    WHERE 1 - (embedding <=> $1) > 0.65
                    ORDER BY embedding <=> $1
                    LIMIT $2
                """, str(query_vector), limit)
                for row in rows:
                    results.append(f"- [{row['category']}] {row['term']}: {row['definition']}")
            except Exception as e:
                print(f"❌ 知識搜尋錯誤: {e}")

        return "\n".join(results) if results else ""

    # =========================================================================
    # 🖼️ 圖片雜湊 (Image Hashing)
    # =========================================================================

    async def check_image_hash(self, img_hash: str) -> Optional[Dict[str, Any]]:
        """
        檢查圖片是否已存在 (重複偵測)。
        """
        async with self.pool.acquire() as conn:
            try:
                row = await conn.fetchrow("""
                    SELECT user_id, created_at, description FROM image_memory
                    WHERE hash = $1
                """, img_hash)
                if row:
                    return {
                        "user_id": row['user_id'],
                        "created_at": row['created_at'],
                        "description": row['description']
                    }
            except Exception as e:
                print(f"❌ 圖片雜湊查詢錯誤: {e}")
        return None

    async def add_image_hash(self, img_hash: str, user_id: str, description: str = ""):
        """
        儲存圖片雜湊 (重複偵測用)。
        """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO image_memory (hash, user_id, description)
                    VALUES ($1, $2, $3)
                    ON CONFLICT (hash) DO NOTHING
                """, img_hash, user_id, description)
                print(f"🖼️ 圖片雜湊已儲存: {img_hash[:8]}... (使用者: {user_id})")
            except Exception as e:
                print(f"❌ 圖片雜湊寫入錯誤: {e}")


# 單元測試
if __name__ == "__main__":
    from dotenv import load_dotenv
    load_dotenv("/home/terraria/servers/.env")

    async def main():
        db_url = os.getenv("DATABASE_URL")
        api_key = os.getenv("GEMINI_API_KEY")

        if not db_url or not api_key:
            print("缺少環境變數")
            return

        manager = MemoryManager(db_url, api_key)
        await manager.init_pool(min_size=1, max_size=3)

        # 測試 1: 新增記憶
        print("💾 儲存記憶中...")
        await manager.add_memory("TestUser", "我喜歡吃拉麵，但不喜歡加蔥。", importance=8)

        # 測試 2: 搜尋記憶
        print("\n🔍 搜尋: '喜歡吃什麼？'")
        results = await manager.search_memory("喜歡吃什麼？")
        for res in results:
            print(f"  找到: {res['content']} (相似度: {res['similarity']:.4f})")

        # 測試 3: 事實
        print("\n📝 新增事實...")
        await manager.add_fact("test_user", "喜歡打 Minecraft")
        facts = await manager.get_facts("test_user")
        print(f"  事實: {facts}")

        await manager.close_pool()

    asyncio.run(main())
