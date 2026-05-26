"""
Google ADK Mem0MemoryService 單元測試與功能驗證腳本
"""
import os
import sys
import asyncio
from google.genai import types

# 1. 載入專案的環境變數 .env
dotenv_path = "/home/hi6688/servers/.env"
if os.path.exists(dotenv_path):
    with open(dotenv_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()
    print("✅ .env 環境變數已成功載入！")
else:
    print("⚠️ 未找到 .env 檔案，將使用當前環境變數。")

# 2. 將專案根目錄與 discord_bot 加入系統路徑，以利導入 utils
sys.path.append("/home/hi6688/servers")
sys.path.append("/home/hi6688/servers/discord_bot")

from utils.memory_manager import MemoryManager
from utils.memory_service import Mem0MemoryService

# 模擬 Session 結構以供測試
class MockPart:
    def __init__(self, text):
        self.text = text

class MockTurn:
    def __init__(self, role, parts):
        self.role = role
        self.parts = parts

class MockSession:
    def __init__(self, session_id, history=None):
        self.session_id = session_id
        self.history = history or []

async def main():
    db_url = os.getenv("DATABASE_URL")
    api_key = os.getenv("GEMINI_API_KEY")

    if not db_url or not api_key:
        print("❌ 錯誤：未設定 DATABASE_URL 或 GEMINI_API_KEY，測試中止。")
        return

    print("🔌 正在初始化 MemoryManager...")
    mm = MemoryManager(db_url=db_url, google_api_key=api_key)
    await mm.init_pool(min_size=1, max_size=2)
    print("🧠 MemoryManager 初始化完成且連線池已啟動。")

    print("\n🛠️ 正在初始化 Mem0MemoryService 原生記憶服務...")
    memory_service = Mem0MemoryService(mm)
    print("✅ Mem0MemoryService 原生對接成功。")

    # 定義一個獨立的測試 user_id
    test_user_id = "test_user_adk_integration"

    try:
        # 🧪 測試一：手動插入一筆長期事實，驗證 search_memory 能否原生檢索並包裹為 ADK 回傳
        print("\n🧪 [TEST 1] 測試原生記憶檢索 search_memory ...")
        
        # 先清除該 user 的可能舊事實，確保乾淨
        # 使用 mm.memory_layer.delete_all 或是 delete
        try:
            mm.memory_layer.delete_all(user_id=test_user_id)
            print("🧹 已清理測試用戶的舊記憶庫")
        except Exception as e:
            print(f"⚠️ 清理舊記憶時發生錯誤（可能是首次測試）：{e}")

        test_fact = "這個測試用戶喜歡吃草莓冰淇淋，並且有一隻叫小橘的貓。"
        print(f"💾 正在為測試用戶 {test_user_id} 寫入事實: '{test_fact}'")
        await mm.add_fact(user_id=test_user_id, fact=test_fact)

        # 呼叫 search_memory 進行檢索
        print(f"🔍 正在調用 search_memory 檢索長期記憶...")
        response = await memory_service.search_memory(
            app_name="HiHiDiscordBot",
            user_id=test_user_id,
            query="他喜歡吃什麼冰淇淋？"
        )

        assert response is not None, "search_memory 返回了 None"
        assert len(response.memories) > 0, "search_memory 未能載入任何事實"
        
        facts_text = response.memories[0].content.parts[0].text
        print(f"🎉 [TEST 1] search_memory 檢索成功！")
        print(f"   - 包裝型別: {type(response)}")
        print(f"   - 注入 Context:\n{facts_text}")
        assert "strawberry" in facts_text.lower() or "草莓" in facts_text, "檢索出的事實與寫入的事實不符"

        # 🧪 測試二：模擬一輪對話結束，驗證 add_session_to_memory 自動回調落盤事實
        print("\n🧪 [TEST 2] 測試對話結束事實自動落盤 add_session_to_memory ...")
        
        # 模擬一輪 User 的新發言
        user_new_input = "我昨天晚上去夜跑，現在雙腿超級酸痛。"
        mock_turn = MockTurn(
            role="user",
            parts=[MockPart(text=user_new_input)]
        )
        mock_session = MockSession(
            session_id=test_user_id,
            history=[mock_turn]
        )

        print(f"📨 模擬對話結束回調，傳入新發言：'{user_new_input}'")
        await memory_service.add_session_to_memory(mock_session)

        # 等待 Mem0 非同步處理並落盤（給予 5 秒緩衝）
        print("⏳ 等待事實寫入與 spaCy/pgvector 衝突分析落盤...")
        await asyncio.sleep(5)

        # 檢索事實庫，驗證是否成功提煉出新事實
        print("🔍 重新檢索事實庫以驗證落盤事實...")
        all_facts = await mm.get_facts(user_id=test_user_id)
        print(f"📋 目前該用戶的事實庫總共有 {len(all_facts)} 筆事實：")
        for idx, f in enumerate(all_facts):
            print(f"   {idx + 1}. {f}")

        # 驗證新事實是否已被提取並儲存
        # 比如是否提煉出 "夜跑"、"酸痛" 或 "腿酸" 相關的語意 facts (相容中英文)
        keywords = ["夜跑", "酸痛", "跑步", "腿", "run", "sore", "leg", "night"]
        has_new_fact = any(any(k in f.lower() for k in keywords) for f in all_facts)
        assert has_new_fact, "事實提取落盤失敗，未能找到夜跑相關的新事實"
        print("🎉 [TEST 2] add_session_to_memory 原生落盤與事實提煉驗證成功！")

    finally:
        # 清理測試數據，保持資料庫純淨
        print("\n🧹 正在清理測試產生的事實數據...")
        try:
            mm.memory_layer.delete_all(user_id=test_user_id)
            print("✅ 測試數據清理完畢。")
        except Exception as e:
            print(f"⚠️ 清理測試數據失敗: {e}")

        # 關閉連線池
        print("🔌 正在關閉資料庫連線池...")
        await mm.close_pool()
        print("✅ 連線池已安全關閉。")

if __name__ == "__main__":
    asyncio.run(main())
