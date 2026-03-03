"""
知識觸發測試 (Knowledge Trigger Test)
模擬 `ai_chat.py` 的 System Prompt，測試 AI 是否會呼叫 `learn_knowledge`。
"""
import asyncio
import os
import sys
import json
from dotenv import load_dotenv
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

async def test_trigger():
    if not GEMINI_API_KEY:
        print("❌ 缺少 API KEY")
        return

    from google import genai
    from google.genai import types

    client = genai.Client(api_key=GEMINI_API_KEY)

    # 模擬 System Prompt (簡化版)
    system_instruction = """
    # 【記憶管理協議 (Memory Protocol)】
    你有兩套長期記憶系統，請根據資訊性質選擇正確的工具：

    ### 1. 知識學習 (Knowledge Learning) —— 關於「世界」
    當使用者提到 **伺服器設定、專有名詞、梗 (Slang)、表情符號定義、或遊戲知識** 時：
    - **必須** 使用 `learn_knowledge(term, definition, category)`。
    - **範例**：
    - 使用者：「sand 是烤豬肉的意思」→ `term="sand", definition="烤豬肉", category="Slang"`
    - 使用者：「OIIA 是那隻旋轉貓」→ `term="OIIA", definition="旋轉貓迷因", category="Meme"`
    - 使用者：「這裡的幣值是 1:100」→ `term="幣值", definition="1:100", category="Lore"`

    ### 2. 事實管理 (Fact Management) —— 關於「人」
    當資訊是關於 **特定使用者 (User)** 的屬性、喜好、關係時：
    - **必須** 使用 `manage_fact(action="add", user_id="...", ...)`。

    ### 請主動執行！
    - 不要等待指令。當你發現新知識或新事實，請**立刻**呼叫工具儲存。
    """

    tools = [
        {
            "name": "learn_knowledge",
            "description": "當使用者教你新詞彙、梗、或伺服器設定時使用。這會存入你的[知識庫] (RAG)。",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "term": {"type": "STRING"},
                    "definition": {"type": "STRING"},
                    "category": {"type": "STRING"}
                },
                "required": ["term", "definition", "category"]
            }
        },
        {
            "name": "manage_fact",
            "description": "管理關於使用者的長期事實 (CRUD)。",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "action": {"type": "STRING"},
                    "user_id": {"type": "STRING"},
                    "content": {"type": "STRING"}
                },
                "required": ["action", "user_id", "content"]
            }
        }
    ]

    print("🧪 正在測試 AI 的工具選擇邏輯...")
    
    test_cases = [
        "User: 欸你知道嗎，OIIA 其實是一隻會旋轉的貓咪喔",
        "User: 豬豬其實不喜歡吃辣",
        "User: 伺服器的貨幣叫做 T幣，可以拿來買地皮",
        "User: 我覺得這隻貓很可愛",  # 單純閒聊，應該不觸發工具
    ]

    for user_input in test_cases:
        print(f"\n🗣️ 輸入: {user_input}")
        response = client.models.generate_content(
            model="gemini-3-flash-preview",
            config=types.GenerateContentConfig(
                tools=[{"function_declarations": tools}],
                system_instruction=system_instruction
            ),
            contents=user_input
        )

        found_tool = False
        if response.candidates and response.candidates[0].content.parts:
            for part in response.candidates[0].content.parts:
                if part.function_call:
                    fc = part.function_call
                    print(f"  🔧 觸發工具: {fc.name}")
                    print(f"  📝 參數: {fc.args}")
                    found_tool = True
        
        if not found_tool:
            print("  😶 無工具呼叫 (正常回應)")

if __name__ == "__main__":
    asyncio.run(test_trigger())
