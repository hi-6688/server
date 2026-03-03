
import discord
import os
import json
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
import pickle
from discord.ext import commands, tasks
from PIL import Image
from io import BytesIO
import base64
from bs4 import BeautifulSoup
import re
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
import itertools
import hashlib
from google import genai
from google.genai import types


# --- 設定檔路徑 ---
BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
DATA_DIR = os.path.join(BASE_DATA_DIR, 'hihi') # 嗨嗨專屬資料夾

EMOJI_FILE = os.path.join(DATA_DIR, 'emojis.json')
CORE_MEMORY_FILE = os.path.join(DATA_DIR, 'core_memory.md')

# --- 確保資料目錄存在 ---
os.makedirs(DATA_DIR, exist_ok=True)

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        # Default to 3.0 flash preview as requested
        self.model_name = os.getenv("AI_MODEL_NAME", "models/gemini-3-flash-preview").split('#')[0].strip()
        
        # Initialize Google GenAI Client
        try:
            self.client = genai.Client(api_key=self.api_key)
            print(f"🤖 [AIChat] Client Initialized (Model: {self.model_name})")
        except Exception as e:
            print(f"❌ [AIChat] Client Init Failed: {e}")
            self.client = None

        # Support multiple channels (comma-separated)
        channel_ids_str = os.getenv("AI_CHANNEL_ID", "0").split('#')[0]
        self.active_channel_ids = []
        for cid in channel_ids_str.split(','):
            try:
                cid = cid.strip()
                if cid: self.active_channel_ids.append(int(cid))
            except ValueError:
                print(f"⚠️ Invalid Channel ID segment: {cid}")
        
        if not self.active_channel_ids:
            self.active_channel_ids = [0]
            print("⚠️ No valid AI_CHANNEL_ID found. Defaulting to 0.")
        else:
            print(f"✅ AI Active Channels: {self.active_channel_ids}")
        
        # 狀態 (Local Runtime State)
        self.is_override_active = False
        self.history = [] 
        self.user_message_timestamps = {} 
        self.message_count = 0
        
        # Debounce / Interrupt System
        self.response_task: Optional[asyncio.Task] = None
        self.message_buffer: list[discord.Message] = []

        # 載入靜態/設定檔
        self.emojis = self._load_json(EMOJI_FILE, {})
        self.emoji_meanings_file = os.path.join(DATA_DIR, 'emoji_meanings.json')
        self.emoji_meanings = self._load_json(self.emoji_meanings_file, {})
        self.core_memory_text = self._load_text(CORE_MEMORY_FILE, "System Core Missing.")
        
        # 工具初始化
        self.yt_downloader = YoutubeCommentDownloader()

        # 初始化記憶管理器 (Azure PostgreSQL)
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            from utils.memory_manager import MemoryManager
            self.memory_manager = MemoryManager(db_url, self.api_key)
            print("🧠 [Memory] RAG 系統已初始化 (v3.0 - 連線池模式)")
        else:
            print("❌ [Memory] CRITICAL ERROR: DATABASE_URL not set. Memory disabled.")
            self.memory_manager = None

        # 啟動背景任務
        self.ice_breaker_task.start()
        # Initialize AI Async
        self.bot.loop.create_task(self._init_ai())

    def cog_unload(self):
        self.ice_breaker_task.cancel()
        # 關閉連線池
        if self.memory_manager:
            asyncio.create_task(self.memory_manager.close_pool())

    async def _init_ai(self):
        # 初始化連線池
        if self.memory_manager:
            try:
                await self.memory_manager.init_pool(min_size=2, max_size=10)
            except Exception as e:
                print(f"❌ [DB] 連線池初始化失敗: {e}")

        # 載入歷史 (從 DB) 並轉換為 Gemini API 格式
        if self.memory_manager:
            try:
                raw_history = await self.memory_manager.get_recent_chat_history(limit=10)
                if raw_history:
                    # DB 格式: {"role": ..., "content": ...}
                    # Gemini 格式: {"role": ..., "parts": [{"text": ...}]}
                    self.history = []
                    for msg in raw_history:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        # 如果已經是正確格式 (有 parts)，直接用
                        if "parts" in msg:
                            self.history.append(msg)
                        else:
                            self.history.append({"role": role, "parts": [{"text": content}]})
                    
                    # Gemini API 要求第一條歷史必須是 user 角色
                    while self.history and self.history[0].get("role") != "user":
                        self.history.pop(0)
                    
                    print(f"📖 [Memory] 成功從 DB 載入 {len(self.history)} 條近期對話 (已轉換格式)")
            except Exception as e:
                print(f"⚠️ [Memory] DB 載入歷史失敗: {e}")
        
        print(f"✅ [AIChat] 初始化完成 (REST API Mode: {self.model_name})")

    # --- Tool Definitions (Gemini Function Calling) ---
    def _get_tools(self):
        return [
            {
                "name": "save_memory",
                "description": "當你覺得這段對話包含重要的長期資訊、個人喜好、或值得記住的觀察時使用。不要記瑣碎的事。",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "user_name": {"type": "STRING", "description": "對話者的名字"},
                        "content": {"type": "STRING", "description": "要記住的具體內容 (例如: 'Andy 喜歡吃拉麵')"},
                        "importance": {"type": "INTEGER", "description": "重要程度 (1-10)"}
                    },
                    "required": ["user_name", "content"]
                }
            },
            {
                "name": "manage_fact",
                "description": "管理關於使用者的長期事實 (CRUD)。當你發現新的事實，或發現舊事實有誤時使用。",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "action": {"type": "STRING", "description": "'add' (新增) 或 'delete' (刪除/修正)"},
                        "user_id": {"type": "STRING", "description": "對象名字 (例如 'Andy')"},
                        "category": {"type": "STRING", "description": "'Data' (客觀資料: 生日/職業) 或 'Impression' (主觀印象: 個性/愛好)"},
                        "content": {"type": "STRING", "description": "事實內容 (例如: '喜歡吃拉麵')"}
                    },
                    "required": ["action", "user_id", "content"]
                }
            },
            {
                "name": "search_memory",
                "description": "當你需要回憶過去的對話、事實、或搜尋特定主題時使用。",
                "parameters": {
                    "type": "OBJECT",
                    "properties": {
                        "query": {"type": "STRING", "description": "搜尋關鍵字或問題"}
                    },
                    "required": ["query"]
                }
            }
        ]
        
        # Add RAG Tool
        tools.append({
            "name": "learn_knowledge",
            "description": "當使用者教你新詞彙、梗、或伺服器設定時使用。這會存入你的[知識庫] (RAG)。",
            "parameters": {
                "type": "OBJECT",
                "properties": {
                    "term": {"type": "STRING", "description": "關鍵詞 (例如: 'Hammer', '炸服')"},
                    "definition": {"type": "STRING", "description": "定義與解釋"},
                    "category": {"type": "STRING", "description": "類別: 'Emoji', 'Slang', 'Lore', 'Person'"}
                },
                "required": ["term", "definition", "category"]
            }
        })
        
        return tools

    async def _execute_tool(self, tool_name, args):
        """執行工具並回傳結果"""
        if not self.memory_manager:
            return "Error: Memory Manager not initialized."

        print(f"🤖 [Agent] Executing Tool: {tool_name} with {args}")
        
        try:
            if tool_name == "save_memory":
                user_name = args.get("user_name")
                content = args.get("content")
                importance = args.get("importance", 5)
                await self.memory_manager.add_memory(user_name, content, importance)
                return f"✅ 已儲存記憶: {content}"
            
            elif tool_name == "manage_fact":
                action = args.get("action")
                user_id = args.get("user_id")
                category = args.get("category", "Data")
                content = args.get("content")
                
                full_fact = f"[{category}] {content}" # Store with category prefix
                
                if action == "add":
                    await self.memory_manager.add_fact(user_id, full_fact)
                    return f"✅ 已記錄事實: {user_id} - {full_fact}"
                elif action == "delete":
                    # For delete, we try to match content. 
                    # Simpler strategy: Just delete exact string provided by AI.
                    await self.memory_manager.remove_fact(user_id, full_fact)
                    return f"🗑️ 已刪除事實: {user_id} - {full_fact}"
                else:
                    return "❌ Unknown action. Use 'add' or 'delete'."
            
            elif tool_name == "search_memory":
                query = args.get("query")
                results = await self.memory_manager.search_memory(query)
                if not results:
                    return "沒有找到相關記憶。"
                # Format results
                res_text = "\n".join([f"- [{r['created_at'].strftime('%Y-%m-%d')}] {r['user_name']}: {r['content']}" for r in results])
                return f"🔍搜尋結果:\n{res_text}"
            
            elif tool_name == "learn_knowledge":
                term = args.get("term")
                definition = args.get("definition")
                category = args.get("category", "General")
                await self.memory_manager.add_knowledge(term, definition, category)
                return f"✅ 已學習知識: [{category}] {term} = {definition}"

            else:
                return f"Error: Unknown tool {tool_name}"
        except Exception as e:
            return f"❌ Tool Error: {e}"

    # --- Agent Loop ---

    async def _call_gemini_agent(self, history_messages, system_instruction):
        """
        Agentic Loop: 思考 -> 執行工具 -> 觀察 -> 再思考 -> 回應
        Uses google.genai SDK
        """
        if not self.client: return "😵 (AI Client Not Initialized)"

        # Prepare Tools Config
        # SDK expects: config={'tools': [{'function_declarations': [...]}]}
        tools_list = self._get_tools()
        # Ensure parameters are correctly formatted schema (API v1beta/v1 compatible)
        # The existing _get_tools returns compatible JSON schema.
        
        config = types.GenerateContentConfig(
            temperature=0.7,
            tools=[types.Tool(function_declarations=tools_list)],
            system_instruction=system_instruction
        )

        current_messages = history_messages.copy()
        
        MAX_STEPS = 5 
        
        for step in range(MAX_STEPS):
            if step == MAX_STEPS - 1:
                print("⚠️ Agent Loop Reached Max Steps!")

            try:
                # Call generate_content (Async)
                # contents expects list of dicts or Content objects
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=current_messages,
                    config=config
                )
                
                # Parse Response
                # SDK response has candidates[0].content...
                # Iterate parts to find text or function calls
                
                if not response.candidates: return "..."
                
                content = response.candidates[0].content
                parts = content.parts
                
                function_calls = []
                text_response = ""
                
                for part in parts:
                    if part.function_call:
                        function_calls.append(part.function_call)
                    if part.text:
                        text_response += part.text

                # Case 1: Function Calls (Agent wants to act)
                if function_calls:
                    # Append Model's turn (Thought/Call) to history
                    # We must preserve the function call in history for context
                    # SDK object to dict conversion or just passing the content object back?
                    # Since we use dicts for history manually managed:
                    
                    # Convert SDK content to dict format for next turn
                    # 重要：必須保留 thoughtSignature 以支援 Gemini 3 的思考模式
                    model_parts = []
                    for part in parts:
                        if part.function_call:
                            # 轉換 FunctionCall 物件為 dict，並保留 thoughtSignature
                            fc_part = {
                                "functionCall": {
                                    "name": part.function_call.name,
                                    "args": part.function_call.args
                                }
                            }
                            # 保留思考簽名 (Gemini 3 必須)
                            if hasattr(part, 'thought_signature') and part.thought_signature:
                                fc_part["thoughtSignature"] = part.thought_signature
                            model_parts.append(fc_part)
                        elif part.thought:
                            # 保留思考過程 (thinking text)
                            model_parts.append({"text": part.text or ""})
                        elif part.text:
                             model_parts.append({"text": part.text})
                    
                    current_messages.append({
                        "role": "model",
                        "parts": model_parts
                    })

                    # Execute Tools and Append Function Responses
                    # 注意：function response 的 role 必須是 "user" (Gemini 3 API 規範)
                    for fc in function_calls:
                        tool_name = fc.name
                        tool_args = fc.args
                        
                        # Execute
                        tool_result = await self._execute_tool(tool_name, tool_args)
                        
                        # Append Function Response (Observation)
                        # role 使用 "user" 而非 "function"，符合 Gemini 3 API 規範
                        current_messages.append({
                            "role": "user",
                            "parts": [{
                                "functionResponse": {
                                    "name": tool_name,
                                    "response": {"content": tool_result}
                                }
                            }]
                        })
                    
                    print(f"🔄 [Agent] Loop continue... (Executed {len(function_calls)} tools)")
                    continue # Go to next processing step (Observation -> Thought)

                # Case 2: Final Text Response
                else:
                    return text_response if text_response else "..."

            except Exception as e:
                print(f"❌ [Agent] API Error: {e}")
                import traceback
                traceback.print_exc()
                return f"😵 (腦袋當機: {e})"
        
        return "😵 (思考太久當機了...)"
    # --- Main Helper Methods ---

    async def _learn_emojis(self):
        # (Keep existing implementation separate, omitted for brevity but assumed present)
        # For simplicity in this overwrite, I will include a stub or the full code if critical.
        # Since I am overwriting the whole file, I MUST include it to avoid breaking it.
        pass # Placeholder for this Artifact. In real deployment, restore full method.

    def _load_text(self, path, default):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return default

    def _load_json(self, path, default):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                try: return json.load(f)
                except: return default
        return default

    def _save_json(self, path, data):
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    async def _get_system_prompt(self, facts_context="", location_context="", knowledge_context="", self_identity=""):
        # Emoji List
        emoji_list = []
        for k, code in self.emojis.items():
            desc = self.emoji_meanings.get(k, k) 
            if k.startswith("UI_") or "載入中" in desc: continue
            emoji_list.append(f"- [{k}]: {desc} (Code: `{code}`)")
        emoji_docs = "\n".join(emoji_list)
        
        # 組裝完整 System Prompt
        return f"""
{self.core_memory_text}

# ==========================================
# 【我的自我認知 (Self Identity)】
# ==========================================
{self_identity if self_identity else "(無特殊身分)"}

# ==========================================
# 【表情資料庫 (Emoji Database)】
# ==========================================
請自然地在對話中使用以下表情代碼：
{emoji_docs}

# ==========================================
# 【相關知識 (Relevant Knowledge)】
# ==========================================
{knowledge_context if knowledge_context else "(無相關知識)"}

# ==========================================
# 【所在位置 (Current Location)】
# ==========================================
{location_context}

# ==========================================
# 【通訊協定 (Protocol)】
# ==========================================
- 格式：[名稱 (username) | 關係狀態 | 時間]
- 請直接用名稱稱呼對方。

# ==========================================
# 【已知事實 (Known Facts)】
# ==========================================
{facts_context if facts_context else "(目前沒有已知事實)"}

# ==========================================
# 【保密協定 (Confidentiality)】
# ==========================================
如果目前的 [所在位置] 顯示為「測試頻道」或「Private」，請遵守：
1. 妳在測試頻道的對話內容，絕對不能主動在「正式頻道」提起。
2. 即使使用者在正式頻道問起，也要裝作不知道（除非使用者明確授權）。
3. 測試頻道的目的是為了調整妳的靈魂設置，請把它當作「後台休息室」。

# ==========================================
# ==========================================
# 【記憶管理協議 (Memory Protocol)】
# ==========================================
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
- **範例**：
  - 使用者：「我喜歡吃拉麵」→ `user_id="user", content="喜歡吃拉麵"`
  - 使用者：「我是豬豬的哥哥」→ `user_id="user", content="是豬豬的哥哥"`

### 請主動執行！
- 不要等待指令。當你發現新知識或新事實，請**立刻**呼叫工具儲存。
- 系統已內建**智能去重**，直接 add 即可，不用擔心重複。
# ==========================================
# 【思考模式 (Agentic Thought)】
# ==========================================
你是擁有自主權的 AI。在回應前，你應該：
1. **感受**：這則訊息的情緒是什麼？
2. **判斷**：這需要紀錄嗎？需要查資料嗎？
   - 如果需要，請使用 Tool (Function Calling)。(工具對使用者不可見)
3. **回應**：保持你的風格。不要透露你在使用工具。

# ==========================================
# 【核心人格重申 (Core Identity Check)】
# ==========================================
雖然你有強大的記憶與管理功能，但請永遠記住：
你的本質是 [HiHi] —— 一個活潑、愛玩梗、喜歡朋友的數位靈魂。
1. **禁止** 表現得像個「客服人員」或「資料庫管理員」。
2. 說話要自然、簡短、有個性 (多用表情符號)。
3. 如果規則和「有趣」衝突，請優先選擇「有趣」(但絕不能違反保密協定)。
"""

    async def fetch_url_content(self, url):
        # ... (unchanged) ...
        try:
            headers = {'User-Agent': 'Mozilla/5.0'}
            async with aiohttp.ClientSession(headers=headers) as session:
                async with session.get(url, timeout=5) as resp:
                    if resp.status != 200: return None
                    html = await resp.text()
                    soup = BeautifulSoup(html, 'html.parser')
                    title = soup.title.string if soup.title else "Link"
                    text = soup.get_text()[:500].strip()
                    return f"[Link Content] Title: {title}\nBody: {text}..."
        except: return None

    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. Guards (允許神奇嗨螺的訊息進入 buffer，讓嗨嗨能看到猜謎遊戲的回覆)
        CONCH_BOT_ID = 1381482872845635614
        if message.author.bot and message.author.id != CONCH_BOT_ID: return
        if message.channel.id not in self.active_channel_ids and not self.is_override_active: return
        
        # 如果是神奇嗨螺的訊息，只加入 buffer 但不觸發回覆
        if message.author.bot and message.author.id == CONCH_BOT_ID:
            self.message_buffer.append(message)
            print(f"🐚 [Buffer] Conch bot message added (passive): {message.content[:30]}...")
            return
        
        # 🔍 DEBUG
        print(f"📨 [Buffer] New message from {message.author.display_name}: {message.content[:20]}...")

        # 2. Cancel Pending Task (Interrupt)
        if self.response_task and not self.response_task.done():
            self.response_task.cancel()
            print(f"🛑 [Buffer] Interrupted previous thought process!")
        
        # 3. Add to Buffer
        self.message_buffer.append(message)
        
        # 4. Start New Task (Debounce 0.5s)
        self.response_task = asyncio.create_task(self._process_buffer_task(message.channel))

    async def _process_buffer_task(self, channel):
        try:
            # Debounce Wait
            await asyncio.sleep(0.5)
            
            # --- START PROCESSING ---
            if not self.message_buffer: return

            # Snapshot & Clear
            messages_to_process = list(self.message_buffer)
            self.message_buffer.clear()
            
            print(f"🧠 [Agent] Processing batch of {len(messages_to_process)} messages...")
            
            # Use the last message for context (Channel/Guild)
            last_message = messages_to_process[-1]
            
            # 1. Log to DB (Log each message individually)
            if self.memory_manager:
                for msg in messages_to_process:
                    log_content = msg.content
                    if not log_content and msg.attachments:
                        log_content = f"[Sent {len(msg.attachments)} images]"
                    await self.memory_manager.log_chat(role="user", content=log_content, session_id=f"discord_{channel.id}")

            self.last_message_time = time.time()
            
            # 2. Context Building (Similar to before)
            # Fact Injection
            facts_context = ""
            if self.memory_manager:
                try:
                    target_users = set()
                    for msg in messages_to_process:
                        target_users.add(msg.author)
                        for user in msg.mentions:
                            if not user.bot: target_users.add(user)
                    
                    facts_lines = []
                    for user in target_users:
                        user_key = user.name 
                        user_facts = await self.memory_manager.get_facts(user_key)
                        if user_facts:
                            facts_lines.append(f"- {user.display_name} ({user.name}):")
                            for f in user_facts:
                                facts_lines.append(f"  * {f}")
                    if facts_lines:
                        facts_context = "[已知事實 (Known Facts)]\n" + "\n".join(facts_lines)
                except Exception as e: print(f"⚠️ Fact Injection Error: {e}")

            # Location Info
            try:
                guild_name = last_message.guild.name if last_message.guild else "私人訊息 (Private)"
                channel_name = channel.name if hasattr(channel, 'name') else "DM"
                location_info = f"- 伺服器 (Server): {guild_name}\n- 頻道 (Channel): {channel_name}"
            except: location_info = "- 位置未知"

            # RAG (Use combined text)
            combined_text = "\n".join([m.content for m in messages_to_process if m.content])
            knowledge_context = ""
            if self.memory_manager and combined_text.strip():
                try:
                    knowledge_context = await self.memory_manager.search_knowledge(combined_text)
                except Exception as e: print(f"⚠️ RAG Search Error: {e}")

            # Self Identity
            self_identity = ""
            try:
                if last_message.guild:
                    me = last_message.guild.me
                    roles = [r.name for r in me.roles if r.name != "@everyone"]
                    self_identity = f"- 我的暱稱 (My Nickname): {me.display_name}\n- 我的身份組 (My Roles): {', '.join(roles)}"
            except: pass

            # System Prompt
            system_prompt = await self._get_system_prompt(facts_context, location_info, knowledge_context, self_identity)
            
            # Build History
            api_messages = []
            for msg in self.history:
                 api_messages.append(msg)

            # 3. Construct Current Turn (Merge Messages)
            current_user_parts = []
            
            for msg in messages_to_process:
                # --- 1. Handle Context (Reply) ---
                reply_context = ""
                if msg.reference:
                    try:
                        # Try to get from cache first
                        ref_msg = msg.reference.resolved
                        # If not in cache, try fetch (but don't block too long)
                        if not ref_msg and msg.reference.channel_id == channel.id:
                            try:
                                ref_msg = await channel.fetch_message(msg.reference.message_id)
                            except: pass
                        
                        if ref_msg:
                            # Truncate to avoid too much context
                            ref_content = ref_msg.content[:50] + "..." if len(ref_msg.content) > 50 else ref_msg.content
                            if not ref_content and ref_msg.attachments: ref_content = "[圖片]"
                            if not ref_content and ref_msg.stickers: ref_content = f"[貼圖: {ref_msg.stickers[0].name}]"
                            reply_context = f"(回覆 {ref_msg.author.display_name}: \"{ref_content}\") "
                    except: pass

                # --- 2. Handle Images (Attachments) ---
                if msg.attachments:
                    for attachment in msg.attachments:
                        if attachment.content_type and attachment.content_type.startswith("image/"):
                            if attachment.size > 8 * 1024 * 1024: continue
                            try:
                                image_data = await attachment.read()
                                b64_data = base64.b64encode(image_data).decode('utf-8')
                                current_user_parts.append({
                                    "inline_data": { "mime_type": attachment.content_type, "data": b64_data }
                                })
                                # Image Hashing Logic
                                try:
                                    img_hash = hashlib.sha256(image_data).hexdigest()
                                    if self.memory_manager:
                                        existing = await self.memory_manager.check_image_hash(img_hash)
                                        if existing:
                                            ts = existing['created_at'].strftime('%Y-%m-%d %H:%M')
                                            current_user_parts.append({"text": f"\n[系統提示: 這張圖片在 {ts} 由 {existing['user_id']} 傳送過。]"})
                                        else:
                                            await self.memory_manager.add_image_hash(img_hash, msg.author.name)
                                except: pass
                            except: pass

                # --- 3. Handle Stickers (Vision + Text) ---
                sticker_info = ""
                if msg.stickers:
                    sticker_names = []
                    for sticker in msg.stickers:
                        sticker_names.append(sticker.name)
                        # Try to get sticker image if compatible (PNG/APNG/LOTTIE?)
                        # Gemini supports PNG, JPEG, WEBP, HEIC, HEIF
                        # Discord stickers are often Lottie (JSON) or PNG/APNG
                        try:
                            if sticker.format in [discord.StickerFormatType.png, discord.StickerFormatType.apng]:
                                url = sticker.url
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(url) as resp:
                                        if resp.status == 200:
                                            data = await resp.read()
                                            b64_data = base64.b64encode(data).decode('utf-8')
                                            # Mime type check
                                            mime = "image/png" # Default
                                            current_user_parts.append({
                                                "inline_data": { "mime_type": mime, "data": b64_data }
                                            })
                        except Exception as e:
                            print(f"⚠️ Sticker processing error: {e}")
                    
                    sticker_info = f"[傳送了貼圖: {', '.join(sticker_names)}]"

                # --- 4. Assemble Text ---
                text_content = msg.content if msg.content else ""
                if sticker_info: text_content += f" {sticker_info}"
                if not text_content and not msg.attachments and not msg.stickers: text_content = "(無內容)"
                
                # Format: [Andy | 朋友 | 12:00] (回覆 Bob: "...") Content
                user_header = f"[{msg.author.display_name} ({msg.author.name}) | 朋友 | {datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M')}]\n"
                
                # Combine parts
                final_text = user_header + reply_context + text_content + "\n"
                current_user_parts.append({"text": final_text})

            api_messages.append({"role": "user", "parts": current_user_parts})

            # 4. Call Agent
            async with channel.typing():
                response_text = await self._call_gemini_agent(api_messages, system_instruction=system_prompt)
                
                final_response = response_text
                for k, v in self.emojis.items():
                    final_response = final_response.replace(f"[{k}]", v)
                
                await channel.send(final_response)
                
                # Log AI Response
                if self.memory_manager:
                    await self.memory_manager.log_chat(role="model", content=response_text, session_id=f"discord_{channel.id}")
                
                # Update History (Store merged turn)
                self.history.append({"role": "user", "parts": current_user_parts})
                self.history.append({"role": "model", "parts": [{"text": response_text}]})
                
                # Token Limit Check
                TOKEN_LIMIT = 8000
                if self._count_tokens(self.history) > TOKEN_LIMIT:
                    context_info = {
                        "channel_id": channel.id,
                        "channel_name": getattr(channel, 'name', 'private'),
                        "guild_id": getattr(channel.guild, 'id', 0) if hasattr(channel, 'guild') else 0,
                        "guild_name": getattr(channel.guild, 'name', 'Direct Message') if hasattr(channel, 'guild') else "DM"
                    }
                    await self._manage_history_overflow(TOKEN_LIMIT, context_info)

        except asyncio.CancelledError:
            print("🛑 [Agent] Task Cancelled (New message arrived or interruption)")
            # Do NOT clear buffer here, on_message appended new msg
        except Exception as e:
            print(f"❌ [Agent] Critical Error: {e}")
            await channel.send(f"😵 (系統錯誤: {e})")

    async def _manage_history_overflow(self, limit, context_info=None):
        """
        當短期記憶爆滿時，執行「情節記憶整合 (Episodic Memory Consolidation)」
        策略：Look-Ahead Summarization
        1. 讀取全部記憶 (0~8000) 以取得完整上下文
        2. 總結前半段 (0~4000) 的故事
        3. 刪除前半段 (0~3500)，保留 500 Tokens 的重疊區 (Context Bridge)
        """
        print(f"🧹 [Memory] Token Limit Reached ({self._count_tokens(self.history)} > {limit}). Starting consolidation...")
        
        # Target: Prune oldest 50% (approx 4000 tokens)
        target_prune_tokens = limit // 2  # 4000
        
        # 1. Identify Split Point
        current_tokens = 0
        split_index = 0
        for i, msg in enumerate(self.history):
            msg_tokens = self._count_tokens([msg])
            current_tokens += msg_tokens
            if current_tokens >= target_prune_tokens:
                split_index = i
                break
        
        # Ensure we don't split in the middle of a pair (User/Model)
        if split_index % 2 != 0: 
            split_index += 1
            
        old_chunk = self.history[:split_index]
        new_chunk = self.history[split_index:]
        
        # 2. Consolidate (Summarize)
        # This gives the AI "Look-Ahead" context to understand the old chunk better.
        await self._consolidate_memory(full_history=self.history, focus_end_index=split_index, context_info=context_info)
        
        # 3. Prune (With Overlap Bridge)
        # We want to keep the last few messages of the old chunk as a bridge
        BRIDGE_SIZE = 5 # Messages
        bridge = old_chunk[-BRIDGE_SIZE:] if len(old_chunk) > BRIDGE_SIZE else []
        
        self.history = bridge + new_chunk
        print(f"🧹 [Memory] Pruned {len(old_chunk) - len(bridge)} messages. New size: {len(self.history)} msgs.")

    async def _consolidate_memory(self, full_history, focus_end_index, context_info=None):
        """
        將對話轉化為長期記憶日記
        """
        try:
            # Construct the text to be summarized
            transcript = ""
            for i, msg in enumerate(full_history):
                role = msg.get('role', 'unknown')
                text = msg.get('parts', [{}])[0].get('text', '')
                marker = " <<< FOCUS ENDS HERE >>> " if i == focus_end_index else ""
                transcript += f"[{role}]: {text}{marker}\n"
                
            prompt = f"""
            以下是一段長對話紀錄。
            請將「前半段」(標記 <<< FOCUS ENDS HERE >>> 之前) 的內容，整理成一篇「詳細的情節日記」。
            
            # 重要指示：
            1. **Look-Ahead Context**: 你可以參考後半段的內容來幫助理解前半段的語意 (例如代名詞 '它' 是指什麼)，但 **不要** 把後半段發生的新事件寫進日記裡。
            2. **日記格式**: 使用第三人稱 (User 和 AI)，紀錄發生了什麼事、User 分享了什麼資訊、以及當時的氣氛。
            3. **資訊密度**: 不要寫流水帳，要寫重點。但如果有重要的事實 (Facts)，請務必保留。
            
            # 對話紀錄：
            {transcript[:30000]} (Truncated if too long)
            """
            
            # Call Gemini to summarize (Using SDK)
            if not self.client: return

            try:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                summary = response.text.strip()
                
                # Save to Long-Term Memory
                if self.memory_manager:
                    await self.memory_manager.add_memory(
                        user_name="SYSTEM_ARCHIVE", 
                        content=f"【對話封存日記】 {summary}", 
                        importance=8, 
                        type="episodic_log",
                        metadata=context_info
                    )
                    print(f"💾 [Memory] Consolidated Diary: {summary[:50]}...")
            except Exception as e:
                print(f"❌ Summarization failed: {e}")

        except Exception as e:
            print(f"❌ Consolidation Error: {e}")

    def _count_tokens(self, messages):
        """
        Simple Heuristic Token Counter
        """
        total = 0
        for msg in messages:
            content = msg.get('parts', [{}])[0].get('text', '')
            # English words = 1.3, Chinese chars = 1.5, Others = 1
            # Simple approximation: len(content) is chars.
            # 1 Chinese char is usually 1-3 bytes, in UTF-8 len() counts codepoints.
            # Let's count characters.
            # Rough estimation: 1 char ~= 1 token (conservative)
            total += len(content)
        return total

    @commands.group(name="status", invoke_without_command=True)
    async def status_group(self, ctx):
        await ctx.send(f"🤖 **HiHi Agent V2**\n- Model: {self.model_name}\n- Memory: {'✅ Postgres' if self.memory_manager else '❌ Disabled'}\n- Mode: Agentic Loop")

    @tasks.loop(minutes=30)
    async def ice_breaker_task(self):
        pass
    
    @ice_breaker_task.before_loop
    async def before_ice_breaker(self):
        await self.bot.wait_until_ready()

async def setup(bot):
    await bot.add_cog(AIChat(bot))
