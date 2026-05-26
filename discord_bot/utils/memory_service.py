"""
HiHi 記憶服務原生對接組件 v1.0
Google ADK BaseMemoryService 實現

功能：
- 繼承 google.adk.memory.BaseMemoryService。
- 實作 search_memory：自動從 Mem0 向量庫中撈取 Facts，並包裝成 ADK 規格的 SearchMemoryResponse 實時注入對話。
- 實作 add_session_to_memory：對話結束後自動回調，提取事實落盤至 PostgreSQL。
"""

from __future__ import annotations
from typing import TYPE_CHECKING, Any
from google.genai import types
from google.adk.memory.base_memory_service import BaseMemoryService, SearchMemoryResponse
from google.adk.memory.memory_entry import MemoryEntry

if TYPE_CHECKING:
    from google.adk.sessions.session import Session
    from discord_bot.utils.memory_manager import MemoryManager

class Mem0MemoryService(BaseMemoryService):
    def __init__(self, memory_manager: MemoryManager):
        """
        初始化記憶服務。
        memory_manager: 本地 MemoryManager 實例
        """
        self.mm = memory_manager
        print("🧠 [ADK MemoryService] 原生記憶服務已加載！")

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
        ADK 內部會自動將其作為 Context 注入給 Gemini。
        """
        try:
            # 透過 Mem0 獲取該使用者的所有事實 (內含 SpaCy NLP 實體加權)
            facts = await self.mm.get_facts(user_id=user_id)
            
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
        我們在這裡提取最後一輪對話（User 說的話與 Model 的回答），
        智慧調用 Mem0 進行事實提取與 In-place 衝突落盤。
        """
        try:
            # 確保 session 有歷史對話
            if not session.history:
                return

            user_id = session.session_id
            last_turn = session.history[-1]

            # 我們只提煉 User 發言中的 Facts
            if last_turn.role == "user":
                # 取得 Content 物件中的 parts 文本
                parts_text = []
                for part in last_turn.parts:
                    if part.text:
                        parts_text.append(part.text)
                
                content_str = " ".join(parts_text).strip()
                if content_str:
                    print(f"💾 [ADK Memory] 偵測到對話結束，正在自動提取 facts 落盤: {user_id} -> '{content_str[:25]}...'")
                    # 使用 Mem0 的強一致性實時寫入管道進行 facts 分析與儲存
                    await self.mm.add_fact(user_id=user_id, fact=content_str)

        except Exception as e:
            print(f"❌ [ADK Memory] 自動落盤錯誤: {e}")
