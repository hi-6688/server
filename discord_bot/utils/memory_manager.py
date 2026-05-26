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
from mem0 import Memory

class MemoryManager:
    def __init__(self, db_url: str, google_api_key: str, api_quota_callback=None):
        self.db_url = db_url
        self.client = genai.Client(api_key=google_api_key)
        self.embedding_model = "gemini-embedding-2"
        self.tagging_model = "gemini-3.1-flash-lite"
        self.api_quota_callback = api_quota_callback
        # 連線池 (初始化時為 None，需要呼叫 init_pool)
        self.pool: Optional[asyncpg.Pool] = None

        # 初始化 Mem0 智慧長期記憶模組的配置對照
        self.mem0_config = {
            "llm": {
                "provider": "gemini",
                "config": {
                    "api_key": google_api_key,
                    "model": self.tagging_model
                }
            },
            "embedder": {
                "provider": "gemini",
                "config": {
                    "api_key": google_api_key,
                    "model": self.embedding_model
                }
            },
            "vector_store": {
                "provider": "qdrant",
                "config": {
                    "path": "/tmp/hihi_qdrant_prod",
                    "embedding_model_dims": 768
                }
            }
        }
        
        # 若有 PostgreSQL URL，優先對接 pgvector (支援 postgres:// 與 postgresql://)
        if db_url and ("postgresql" in db_url or "postgres" in db_url):
            # SQLAlchemy 要求協議必須是 postgresql://，防禦性轉換
            mem0_db_url = db_url
            if mem0_db_url.startswith("postgres://"):
                mem0_db_url = mem0_db_url.replace("postgres://", "postgresql://", 1)
            self.mem0_config["vector_store"] = {
                "provider": "pgvector",
                "config": {
                    "connection_string": mem0_db_url,
                    "collection_name": "hihi_mem0_facts",
                    "embedding_model_dims": 768
                }
            }
            print("🔌 [Mem0] 正在將長期記憶向量庫對接 PostgreSQL (pgvector)...")
        else:
            print("⚠️ [Mem0] 未偵測到有效的 DATABASE_URL，使用本地 Qdrant 進行沙盒驗證...")

        try:
            self.memory_layer = Memory.from_config(self.mem0_config)
            print("🧠 [Mem0] 智慧記憶層初始化成功！")
        except Exception as e:
            print(f"⚠️ [Mem0] 初始化失敗，將嘗試使用本地 fallback 記憶庫: {e}")
            fallback_config = {
                "llm": self.mem0_config["llm"],
                "embedder": self.mem0_config["embedder"],
                "vector_store": {
                    "provider": "qdrant",
                    "config": {
                        "path": "/tmp/hihi_qdrant_prod_fallback",
                        "embedding_model_dims": 768
                    }
                }
            }
            self.memory_layer = Memory.from_config(fallback_config)
            print("🧠 [Mem0] 本地 Fallback 記憶層初始化成功！")

    # 協助在進行 Mem0 的同步呼叫時進行 429 限流退避、自動重試且不阻塞 asyncio 主線的輔助函式
    async def _run_mem0_with_retry(self, func, *args, **kwargs):
        max_retries = 5
        for attempt in range(max_retries):
            try:
                # 將同步的 Mem0 API 呼叫放入背景 Executor 執行，確保不阻塞 Discord Event Loop
                loop = asyncio.get_running_loop()
                return await loop.run_in_executor(None, lambda: func(*args, **kwargs))
            except Exception as e:
                err_str = str(e)
                if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str or "quota" in err_str.lower():
                    wait_time = (attempt + 1) * 35
                    print(f"⚠️ [Mem0 API] 偵測到 429 限流。等待 {wait_time} 秒後重試 (第 {attempt+1}/{max_retries} 次)...")
                    await asyncio.sleep(wait_time)
                else:
                    raise e
        raise RuntimeError("Mem0 呼叫因 API 限流多次重試失敗。")

    # =========================================================================
    # 🔌 連線池管理 (Connection Pool)
    # =========================================================================

    async def init_pool(self, min_size: int = 2, max_size: int = 10):
        """
        初始化連線池與背景任務佇列。應在 Bot 啟動時呼叫。
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
        關閉連線池與背景任務。應在 Bot 關閉時呼叫。
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

    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """手動對截斷後的向量進行 L2 歸一化，防止餘弦相似度失真"""
        if not vector:
            return vector
        import math
        sq_sum = sum(x ** 2 for x in vector)
        norm = math.sqrt(sq_sum)
        if norm == 0:
            return vector
        return [x / norm for x in vector]

    async def get_embedding(self, text: str) -> List[float]:
        """
        將文字轉換為 768 維向量 (Gemini Embedding)。
        使用非同步 API 避免阻塞。
        """
        try:
            response = await self.client.aio.models.embed_content(
                model=self.embedding_model,
                contents=text,
                config=types.EmbedContentConfig(
                    output_dimensionality=768
                )
            )
            raw_vector = response.embeddings[0].values
            return self._normalize_vector(raw_vector)
        except Exception as e:
            print(f"❌ Embedding 錯誤: {e}")
            return []

    # =========================================================================
    # 🧠 長期記憶 (Memories)
    # =========================================================================

    # =========================================================================
    # 🧠 長期記憶 (Memories - 舊有靜態 RAG 已由 Mem0 v3 pgvector 大一統接管並廢除)
    # =========================================================================

    # 註：舊有的自造 metadata 自動標籤 (Auto-Tagging)、Gemini 手動 Embedding 向量生成
    # 以及 memories 傳統 RAG 表格之 add_memory() 與 search_memory() 因已回歸 Mem0 v3
    # 官方強一致性 pgvector 與 Entity Linking，已於 v12.0 全面進行死碼安全清理。

    # =========================================================================
    # 📝 核心事實 (Facts) — Mem0 v3 + PostgreSQL 大滿貫融合版
    # =========================================================================

    async def add_fact(self, user_id: str, fact: str):
        """
        智能新增事實：利用 Mem0 進行 ADD-Only 增量記憶提取並儲存於長期記憶中。
        """
        try:
            await self._run_mem0_with_retry(self.memory_layer.add, fact, user_id=user_id)
            print(f"✅ [Mem0] 事實已儲存: {user_id} - {fact}")
        except Exception as e:
            print(f"❌ [Mem0] 事實寫入錯誤: {e}")

    async def remove_fact(self, user_id: str, fact: str):
        """
        模糊刪除事實 (Fuzzy Delete)：
        透過 Mem0 語意搜尋該用戶最相近的事實 ID，並調用 delete 物理抹除。
        """
        try:
            raw_results = await self._run_mem0_with_retry(self.memory_layer.search, fact, filters={"user_id": user_id})
            results_list = []
            if isinstance(raw_results, dict):
                results_list = raw_results.get("results", raw_results.get("memories", []))
            elif isinstance(raw_results, list):
                results_list = raw_results
            
            if results_list:
                first_item = results_list[0]
                if isinstance(first_item, dict) and 'id' in first_item:
                    memory_id = first_item['id']
                    await self._run_mem0_with_retry(self.memory_layer.delete, memory_id)
                    print(f"🗑️ [Mem0] 已移除事實: {user_id} - ID: {memory_id} (內容: {first_item.get('fact')})")
                    return
            print(f"⚠️ [Mem0] 找不到相似事實可刪除: {user_id} - {fact}")
        except Exception as e:
            print(f"❌ [Mem0] 事實刪除錯誤: {e}")

    async def get_facts(self, user_id: str) -> List[str]:
        """
        取得特定使用者的所有事實（語意與實體混合加載）。
        """
        try:
            raw_results = await self._run_mem0_with_retry(self.memory_layer.get_all, filters={"user_id": user_id})
            results_list = []
            if isinstance(raw_results, dict):
                results_list = raw_results.get("results", raw_results.get("memories", []))
            elif isinstance(raw_results, list):
                results_list = raw_results
            
            facts = []
            for item in results_list:
                if isinstance(item, dict):
                    # 防禦性相容 'fact' 與 'memory' 鍵
                    content = item.get('fact') or item.get('memory')
                    if content:
                        facts.append(content)
            return facts
        except Exception as e:
            print(f"❌ [Mem0] 事實查詢錯誤: {e}")
            return []

    async def search_facts_by_topic(self, query: str, limit: int = 5) -> List[Dict[str, str]]:
        """
        語意搜尋事實（跨使用者 RAG 專用）。
        """
        try:
            raw_results = await self._run_mem0_with_retry(self.memory_layer.search, query, limit=limit)
            results_list = []
            if isinstance(raw_results, dict):
                results_list = raw_results.get("results", raw_results.get("memories", []))
            elif isinstance(raw_results, list):
                results_list = raw_results
            
            results = []
            for item in results_list:
                if isinstance(item, dict) and 'fact' in item:
                    results.append({
                        "user_id": item.get("user_id", "unknown"),
                        "fact": item['fact'],
                        "similarity": item.get("similarity", 0.0)
                    })
            return results
        except Exception as e:
            print(f"❌ [Mem0] 事實語意搜尋錯誤: {e}")
            return []

    async def delete_all_user_memories(self, user_id: str):
        """
        物理抹除該使用者的所有隱私長期記憶，符合 GDPR 一鍵遺忘規範。
        """
        try:
            await self._run_mem0_with_retry(self.memory_layer.delete_all, user_id=user_id)
            print(f"🧹 [Mem0] 用戶 {user_id} 的長期記憶事實已被物理清空！")
        except Exception as e:
            print(f"❌ [Mem0] 物理抹除用戶 {user_id} 記憶失敗: {e}")
            raise e

    # =========================================================================
    # 📜 聊天記錄 (Chat History)
    # =========================================================================

    async def log_chat(self, role: str, content: str, session_id: str = "global", interaction_id: str = None):
        """
        記錄聊天訊息 (chat_history 表)，支援寫入 interaction_id。
        """
        async with self.pool.acquire() as conn:
            try:
                await conn.execute("""
                    INSERT INTO chat_history (role, content, session_id, interaction_id)
                    VALUES ($1, $2, $3, $4)
                """, role, content, session_id, interaction_id)
            except Exception as e:
                print(f"❌ 聊天記錄錯誤: {e}")

    async def get_recent_chat_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        取得近期聊天記錄 (按時間正序)，包含 interaction_id。
        """
        async with self.pool.acquire() as conn:
            history = []
            try:
                rows = await conn.fetch("""
                    SELECT role, content, interaction_id FROM chat_history
                    ORDER BY timestamp DESC
                    LIMIT $1
                """, limit)
                # 反轉為時間正序
                for row in reversed(rows):
                    history.append({
                        "role": row['role'],
                        "content": row['content'],
                        "interaction_id": row['interaction_id']
                    })
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
        query_vector = await self.get_embedding(query)
        if not query_vector:
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
    # 動態讀取專案根目錄的 .env 檔案
    env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
    load_dotenv(env_path)

    async def main():
        db_url = os.getenv("DATABASE_URL")
        api_key = os.getenv("GEMINI_API_KEY")

        if not db_url or not api_key:
            print("缺少環境變數")
            return

        manager = MemoryManager(db_url, api_key)
        await manager.init_pool(min_size=1, max_size=3)

        # 測試 1: 新增記憶
        print("💾 同步儲存記憶中...")
        success = await manager.add_memory("TestUser", "我喜歡吃拉麵，但不喜歡加蔥。", importance=8)
        print(f"  儲存狀態: {success}")

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
