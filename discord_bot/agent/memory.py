"""
HiHi 記憶服務原生對接組件 v2.0 (Milestone v17.0)
Google ADK BaseMemoryService 實現 (Mem0 v3 原生裝配直連版)

功能：
- 100% 繼承 google.adk.memory.BaseMemoryService。
- 物理消滅對 MemoryManager 的依賴，直接在內部裝配 Mem0 v3 長期事實記憶層。
- 實作 search_memory：自動從 Mem0 向量庫中撈取 Facts，並包裝成 ADK 規格的 SearchMemoryResponse 實時注入對話。
- 實作 add_session_to_memory：對話結束後自動回調，提取事實落盤至 PostgreSQL。
- 實作 delete_all_user_memories：直接封裝 GDPR 一鍵物理銷毀。
"""

from __future__ import annotations
import asyncio
from typing import TYPE_CHECKING, Any, List, Dict
from google.genai import types
from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry
from mem0 import Memory

if TYPE_CHECKING:
    from google.adk.sessions.session import Session

class Mem0MemoryService(BaseMemoryService):
    def __init__(self, db_url: str, google_api_key: str):
        """
        初始化記憶服務，直接裝配 Mem0 v3 智慧記憶層。
        db_url: 資料庫連線字串
        google_api_key: Gemini API 金鑰 (直連官方)
        """
        self.db_url = db_url
        self.google_api_key = google_api_key
        
        # SQLAlchemy 要求協議必須是 postgresql://，防禦性轉換
        mem0_db_url = db_url
        if mem0_db_url and mem0_db_url.startswith("postgres://"):
            mem0_db_url = mem0_db_url.replace("postgres://", "postgresql://", 1)

        # 裝配 Mem0 v3 標準對齊配置
        self.mem0_config = {
            "llm": {
                "provider": "gemini",
                "config": {
                    "api_key": google_api_key,
                    "model": "gemini-3.1-flash-lite"
                }
            },
            "embedder": {
                "provider": "gemini",
                "config": {
                    "api_key": google_api_key,
                    "model": "gemini-embedding-2"
                }
            },
            "vector_store": {
                "provider": "pgvector",
                "config": {
                    "connection_string": mem0_db_url,
                    "collection_name": "hihi_mem0_facts",
                    "embedding_model_dims": 768
                }
            }
        }

        # 實例化官方原生記憶庫
        self.memory_layer = Memory.from_config(self.mem0_config)
        print("🧠 [ADK MemoryService] Mem0 v3 智慧長期事實記憶層裝配完成！")

    async def _run_mem0_with_retry(self, func, *args, **kwargs):
        """協助在進行同步 Mem0 呼叫時進行 429 限流退避、自動重試且不阻塞 asyncio 主執行緒"""
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

    async def delete_all_user_memories(self, user_id: str):
        """
        物理抹除該使用者的所有隱私長期記憶，符合 GDPR 一鍵遺忘規範。
        """
        try:
            await self._run_mem0_with_retry(self.memory_layer.delete_all, user_id=user_id)
            print(f"🧹 [ADK MemoryService] 用戶 {user_id} 的長期記憶事實已被物理清空！")
        except Exception as e:
            print(f"❌ [ADK MemoryService] 物理抹除用戶 {user_id} 記憶失敗: {e}")
            raise e

    async def search_memory(
        self,
        *,
        app_name: str,
        user_id: str,
        query: str,
    ) -> SearchMemoryResponse:
        """
        【自動檢索與注入技術】
        當 Runner 啟動對話時，ADK 會在底層自動調用此函數。
        我們在這裡直接調用 Mem0 撈取該使用者的 Facts，並以 MemoryEntry 回傳。
        """
        try:
            # 直接調用 Mem0 獲取該使用者的所有事實
            raw_results = await self._run_mem0_with_retry(self.memory_layer.get_all, filters={"user_id": user_id})
            results_list = []
            if isinstance(raw_results, dict):
                results_list = raw_results.get("results", raw_results.get("memories", []))
            elif isinstance(raw_results, list):
                results_list = raw_results
            
            facts = []
            for item in results_list:
                if isinstance(item, dict):
                    content = item.get('fact') or item.get('memory')
                    if content:
                        facts.append(content)
            
            if not facts:
                print(f"🔍 [ADK Memory] 檢索用戶 {user_id} 記憶完成：無已存 Facts。")
                return SearchMemoryResponse(memories=[])

            facts_text = "【長期已知事實與偏好庫】\n" + "\n".join(f"- {fact}" for fact in facts)
            print(f"🔍 [ADK Memory] 檢索用戶 {user_id} 記憶完成，共載入 {len(facts)} 條 Facts。")

            # 包裝成 ADK 規格的 MemoryEntry (types.Content)
            content = types.Content(
                parts=[types.Part.from_text(text=facts_text)],
                role="user"
            )
            entry = MemoryEntry(
                content=content,
                id=f"mem0_facts_{user_id}",
                author="Mem0"
            )
            return SearchMemoryResponse(memories=[entry])

        except Exception as e:
            print(f"❌ [ADK Memory] 記憶搜尋錯誤: {e}")
            return SearchMemoryResponse(memories=[])

    async def add_session_to_memory(
        self,
        session: Session,
    ) -> None:
        """
        【對話結束自動落盤技術】
        當一輪對話結束時，ADK Runner 會自動觸發此回調。
        我們在這裡提取最後一輪對話，智慧調用 Mem0 進行事實提取與 In-place 衝突落盤。
        """
        try:
            # 確保 session 有 events
            if not session.events:
                return

            user_id = session.user_id
            
            # 從 events 中尋找最後一個來自 user 的 event
            last_user_event = None
            for event in reversed(session.events):
                if event.author == "user":
                    last_user_event = event
                    break

            if last_user_event and last_user_event.content:
                # 取得 Content 物件中的 parts 文本
                parts_text = []
                if last_user_event.content.parts:
                    for part in last_user_event.content.parts:
                        if part.text:
                            parts_text.append(part.text)
                
                content_str = " ".join(parts_text).strip()
                if content_str:
                    print(f"💾 [ADK Memory] 偵測到對話結束，正在自動提取 facts 落盤: {user_id} -> '{content_str[:25]}...'")
                    # 直接呼叫 Mem0 進行增量提煉與寫入
                    await self._run_mem0_with_retry(self.memory_layer.add, content_str, user_id=user_id)

        except Exception as e:
            print(f"❌ [ADK Memory] 自動落盤錯誤: {e}")

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
                    print(f"🗑️ [Mem0] 已移除事實: {user_id} - ID: {memory_id} (內容: {first_item.get('fact') or first_item.get('memory')})")
                    return
            print(f"⚠️ [Mem0] 找不到相似事實可刪除: {user_id} - {fact}")
        except Exception as e:
            print(f"❌ [Mem0] 事實刪除錯誤: {e}")

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
                if isinstance(item, dict):
                    results.append({
                        "user_id": item.get("user_id", "unknown"),
                        "fact": item.get('fact') or item.get('memory', ''),
                        "similarity": item.get("similarity", 0.0)
                    })
            return results
        except Exception as e:
            print(f"❌ [Mem0] 事實語意搜尋錯誤: {e}")
            return []
