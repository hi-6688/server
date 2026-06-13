import os
import sys
import asyncio
import re
from dotenv import load_dotenv

sys.path.append("/home/hi6688/servers/discord_bot")
from agent.memory import Mem0MemoryService

load_dotenv("/home/hi6688/servers/.env")

async def main():
    api_key = os.getenv("GEMINI_API_KEY")
    db_url = os.getenv("DATABASE_URL")
    
    print("🔌 正在初始化 Mem0MemoryService...")
    memory_service = Mem0MemoryService(db_url=db_url, google_api_key=api_key)
    
    user_id = "test_user_adv"
    user_name = "Andy"
    
    # 清理舊測試記憶
    print("🧹 清理舊測試記憶...")
    await memory_service.delete_all_user_memories(user_id)
    
    # 1. 寫入帶有 guild_A 的記憶
    print("\n📝 1. 寫入 guild_A 的事實...")
    await memory_service.add_memory(
        "Andy喜歡吃豚骨拉麵，不喜歡香菜", 
        user_id=user_id,
        guild_id="guild_A"
    )
    
    # 2. 寫入帶有 global (全域) 的記憶
    print("📝 2. 寫入 global 的事實...")
    await memory_service.add_memory(
        "Andy本名叫陳安迪，今年28歲", 
        user_id=user_id,
        guild_id="global"
    )
    
    # 3. 測試在 guild_B 搜尋 (隔離驗證)
    print("\n🔍 3. 在 guild_B 進行對話檢索...")
    search_res_B = await memory_service.search_memory(
        app_name="HiHiDiscordBot",
        user_id=user_id,
        query="安迪今天想吃拉麵",
        guild_id="guild_B"
    )
    
    print("\n--- [guild_B 搜尋結果] ---")
    facts_text_B = ""
    if search_res_B.memories:
        facts_text_B = search_res_B.memories[0].content.parts[0].text
        print(facts_text_B)
    else:
        print("無結果")
    print("------------------------")
    
    # 驗證：應該包含 "陳安迪" (global)，但絕不包含 "豚骨拉麵" (guild_A)
    assert "陳安迪" in facts_text_B, "❌ 錯誤：global 記憶未被成功載入！"
    assert "豚骨拉麵" not in facts_text_B, "❌ 錯誤：guild_A 的私密記憶在外伺服器 guild_B 洩漏了！"
    print("🟢 跨伺服器隱私隔離驗證成功！")
    
    # 4. 測試在 guild_A 搜尋 (無損驗證)
    print("\n🔍 4. 在 guild_A 進行對話檢索...")
    search_res_A = await memory_service.search_memory(
        app_name="HiHiDiscordBot",
        user_id=user_id,
        query="安迪想吃晚餐",
        guild_id="guild_A"
    )
    
    print("\n--- [guild_A 搜尋結果] ---")
    facts_text_A = ""
    if search_res_A.memories:
        facts_text_A = search_res_A.memories[0].content.parts[0].text
        print(facts_text_A)
    else:
        print("無結果")
    print("------------------------")
    
    assert "陳安迪" in facts_text_A and "豚骨拉麵" in facts_text_A, "❌ 錯誤：本伺服器記憶或全域記憶載入不全！"
    print("🟢 本伺服器加載與軟過濾驗證成功！")
    
    # 5. 測試記憶歷史回溯 (inspect_memory_history)
    print("\n⏳ 5. 測試記憶歷史回溯...")
    ids = re.findall(r"\[id:\s*([a-f0-9\-]+)\]", facts_text_A)
    if ids:
        target_id = ids[0]
        print(f"🎯 找到事實 ID: {target_id}")
        
        # 讀取最相近 Facts 歷史
        print(f"🔍 呼叫 get_memory_history(id={target_id}) ...")
        history_text = await memory_service.get_memory_history(target_id)
        print("\n--- [歷史變更日誌] ---")
        print(history_text)
        print("--------------------")
        assert "歷史演變軌跡" in history_text, "❌ 錯誤：歷史軌跡獲取失敗！"
        print("🟢 記憶歷史追蹤與回溯驗證成功！")
    else:
        print("❌ 未在 Facts 清單中找到 ID，無法測試 history。")
        
if __name__ == "__main__":
    asyncio.run(main())
