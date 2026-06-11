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
import asyncpg
from typing import TYPE_CHECKING, Any, List, Dict, Optional
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
        guild_id: Optional[str] = None, # 💡 新增 guild_id 參數，用於跨伺服器隱私隔離
    ) -> SearchMemoryResponse:
        """
        【自動檢索與注入技術】
        當 Runner 啟動對話時，ADK 會在底層自動調用此函數。
        我們在這裡直接調用 Mem0 撈取該使用者的 Facts，在 Python 記憶體中做「軟過濾」隔離不同伺服器的事實，
        並附帶 ID 注入事實中回傳給 AI。
        """
        try:
            # 撈取該使用者的所有長期事實清單
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
                    # 💡 跨伺服器隱私隔離「軟過濾」邏輯：
                    # 如果記憶不含 guild_id、或者標記為 "global" 全域、或者與當前伺服器 guild_id 一致，則允許載入。
                    metadata = item.get('metadata', {}) or {}
                    fact_guild_id = metadata.get('guild_id')
                    
                    if not fact_guild_id or fact_guild_id == "global" or (guild_id and str(fact_guild_id) == str(guild_id)):
                        if content:
                            fact_id = item.get('id', 'unknown')
                            facts.append((fact_id, content))
            
            if not facts:
                print(f"🔍 [ADK Memory] 檢索用戶 {user_id} 記憶完成：無已存 Facts (過濾後)。")
                return SearchMemoryResponse(memories=[])

            # 💡 格式化 Facts 清單，將 Memory ID 注入最前端，供 AI 閱讀以進行歷史溯源
            facts_text = "【長期已知事實與偏好庫】\n" + "\n".join(f"- [id: {fid}] {fact}" for fid, fact in facts)
            print(f"🔍 [ADK Memory] 檢索用戶 {user_id} 記憶完成，共載入 {len(facts)} 條 Facts (已注入 ID)。")

            # 包裝成 ADK 規格的 MemoryEntry
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
        guild_id: Optional[str] = None
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
                    
                    # 💡 優先使用傳入的 guild_id，若無則自 session.state 中讀取
                    resolved_guild_id = guild_id or (session.state.get("guild_id") if session.state else None)
                    metadata = {"guild_id": resolved_guild_id} if resolved_guild_id else None
                    
                    # 直接呼叫 Mem0 進行增量提煉與寫入，並附加 metadata 標籤
                    await self._run_mem0_with_retry(
                        self.memory_layer.add, 
                        content_str, 
                        user_id=user_id,
                        metadata=metadata
                    )

        except Exception as e:
            print(f"❌ [ADK Memory] 自動落盤錯誤: {e}")

    async def get_memory_history(self, memory_id: str) -> str:
        """
        獲取某條事實 ID 的歷史版本與演變時間軸。
        """
        try:
            # 異步呼叫官方 history 方法，包含 429 退避重試
            raw_history = await self._run_mem0_with_retry(self.memory_layer.history, memory_id)
            if not raw_history:
                return f"🔍 找不到與記憶 ID `{memory_id}` 相關的歷史變更紀錄。"
            
            history_lines = [f"📊 記憶 ID `{memory_id}` 的歷史演變軌跡："]
            
            # Mem0 history 通常回傳一個 list 的 dict
            if isinstance(raw_history, list):
                for idx, record in enumerate(raw_history):
                    timestamp = record.get("created_at") or record.get("updated_at") or "未知時間"
                    event_type = record.get("event") or record.get("action") or "更新"
                    fact_val = record.get("fact") or record.get("memory") or "無內容"
                    history_lines.append(f"  > {idx+1}. [{timestamp}] 操作: `{event_type}`\n    * 內容: \"{fact_val}\"")
            else:
                history_lines.append(f"  > {str(raw_history)}")
                
            return "\n".join(history_lines)
        except Exception as e:
            print(f"❌ [ADK MemoryService] 獲取記憶歷史失敗: {e}")
            return f"❌ 獲取記憶歷史記錄失敗：`{e}`"

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

    async def get_user_impression(self, user_id: str) -> Optional[str]:
        """
        讀取用戶的動態知識 Profile。
        """
        try:
            conn = await asyncpg.connect(self.db_url)
            try:
                row = await conn.fetchrow(
                    "SELECT impression FROM user_impressions WHERE user_id = $1", 
                    user_id
                )
                if row:
                    return row['impression']
                return None
            finally:
                await conn.close()
        except Exception as e:
            print(f"❌ [ADK Memory] 讀取 user_impressions 失敗: {e}")
            return None

    async def save_user_impression(self, user_id: str, user_name: str, impression: str) -> None:
        """
        儲存或更新用戶的動態知識 Profile。
        """
        try:
            conn = await asyncpg.connect(self.db_url)
            try:
                await conn.execute(
                    '''
                    INSERT INTO user_impressions (user_id, user_name, impression, last_updated)
                    VALUES ($1, $2, $3, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        user_name = EXCLUDED.user_name,
                        impression = EXCLUDED.impression,
                        last_updated = CURRENT_TIMESTAMP
                    ''',
                    user_id, user_name, impression
                )
                print(f"💾 [ADK Memory] 成功儲存用戶 {user_name} ({user_id}) 的印象 Profile")
            finally:
                await conn.close()
        except Exception as e:
            print(f"❌ [ADK Memory] 儲存 user_impressions 失敗: {e}")

