
from typing import Optional
import discord
import os
import json
import time
import asyncio
import aiohttp
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
import pickle
from discord.ext import commands, tasks
from PIL import Image
from io import BytesIO
import base64
import re
import itertools
import hashlib
from google import genai
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.tools import AgentTool, url_context # 導入多智能體委派工具與官方內建 url_context 讀網頁工具
from google.adk.telemetry.setup import maybe_set_otel_providers # 導入官方遙測設定
from google.adk.apps.app import App, EventsCompactionConfig # 導入官方 ADK App 容器與事件壓縮配置

# 💡 導入高雅解耦的自製工具與服務模組
from tools.scheduler_tools import execute_sleep_scheduling
from utils.quota_manager import QuotaManager
from utils.telemetry_mirror import TelemetryMirror
from utils.emoji_service import EmojiService

from utils.adk_config import get_session_service # 導入官方 ADK 持久化配置
from utils.memory_service import Mem0MemoryService


# --- 設定檔路徑 ---
BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
DATA_DIR = os.path.join(BASE_DATA_DIR, 'hihi') # 嗨嗨專屬資料夾

EMOJI_FILE = os.path.join(DATA_DIR, 'emojis.json')
CORE_MEMORY_FILE = os.path.join(DATA_DIR, 'core_memory.md')

# --- 確保資料目錄存在 ---
os.makedirs(DATA_DIR, exist_ok=True)

from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional

class MemoryState(BaseModel):
    needs_reply: bool = Field(description="判斷目前對話歷史是否需要我回答。若需要填 True，不需要或決定休眠填 False。")
    current_goal: str = Field(description="我目前的工作目標或要處理的實體。")
    suggested_sleep_seconds: int = Field(description="我決定接下來要主動休眠多久（秒）？這是妳用來保護「生命配額」的唯一手段。若配額充足且群組熱鬧，填 3600；若配額快耗盡，請大膽填寫 14400 或更長，直到下午三點重置。")
    sleep_intent: Optional[str] = Field(default=None, description="如果妳設定了休眠秒數，請在這裡寫下妳『醒來後要做什麼』(例如：『等待60秒後回答問題』)。如果只是普通的長眠，請填 null。")

class PersonaResponse(BaseModel):
    situation_analysis: str = Field(description="簡短分析目前群組的氣氛與上下文脈絡。")
    internal_thought: str = Field(description="妳在心裡的 OS。決定用什麼態度回覆。")
    final_speech: Optional[str] = Field(default=None, description="最後要在 Discord 說出口的話。如果覺得不想回，請填 null。")

class AIChat(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv("GEMINI_API_KEY")
        db_url = os.getenv("DATABASE_URL")
        # 預設使用 gemini-3.1-flash-lite
        self.model_name = os.getenv("AI_MODEL_NAME", "gemini-3.1-flash-lite").split('#')[0].strip()
        
        # Initialize Google GenAI Client
        try:
            api_base = os.getenv("GEMINI_API_BASE")
            if api_base:
                self.client = genai.Client(
                    api_key=self.api_key,
                    http_options=types.HttpOptions(base_url=api_base)
                )
            else:
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
            
        self.inner_world_channel_id = int(os.getenv("INNER_WORLD_CHANNEL_ID", 0))
        
        # 狀態 (Local Runtime State)
        self.is_override_active = False
        self.message_count = 0        
        # Debounce / Interrupt System
        self.response_task: Optional[asyncio.Task] = None
        self.message_buffer: list[discord.Message] = []

        # 💓 心跳引擎 (Async Heartbeat Engine)
        self.heartbeat_task: Optional[asyncio.Task] = None
        self.sensory_interrupt_event = asyncio.Event()
        self.schedule_update_event = asyncio.Event()
        self.next_sleep_duration = 3600
        self.sleep_intent = None
        self.session_service = get_session_service() # 初始化官方 ADK 會話服務

        # 載入靜態/設定檔
        self.daily_limit_requests = 500
        self.usage_file = os.path.join(DATA_DIR, 'daily_usage.json')
        self.emoji_meanings_file = os.path.join(DATA_DIR, 'emoji_meanings.json')
        self.core_memory_text = self._load_text(CORE_MEMORY_FILE, "System Core Missing.")
        
        # 💡 初始化自製工具與服務模組
        self.quota_manager = QuotaManager(usage_file=self.usage_file, daily_limit=self.daily_limit_requests)
        self.emoji_service = EmojiService(emoji_file=EMOJI_FILE, meanings_file=self.emoji_meanings_file)
        self.telemetry_mirror = TelemetryMirror(bot=self.bot, inner_world_channel_id=self.inner_world_channel_id, client=self.client)
        
        # 工具初始化

        # 物理消滅自製 MemoryManager，大腦迎向 100% 官方原生直連
        self.memory_manager = None
        self.file_search_store_name = None  # 官方 File Search Store 名稱

        # 初始化 Google ADK Agent 與 DatabaseSessionService 持久化會話 Runner
        self.runner = None
        if db_url and self.api_key:
            try:
                # 定義長期事實與學習工具 (讓 ADK 自動分析 Schema，完美掛載)
                async def manage_fact_tool(action: str, user_id: str, content: str, category: str = "Data") -> str:
                    """管理關於使用者的長期事實 (CRUD)。當你發現新的事實，或發現舊事實有誤時使用。
                    
                    Args:
                        action: 'add' (新增) 或 'delete' (刪除/修正)
                        user_id: 對象名字 (例如 'Andy')
                        content: 事實內容 (例如: '喜歡吃拉麵')
                        category: 類別，可填 'Data' (客觀資料: 生日/職業) 或 'Impression' (主觀印象: 個性/愛好)
                    """
                    return await self.manage_fact(action, user_id, content, category)

                async def learn_knowledge_tool(term: str, definition: str, category: str = "General") -> str:
                    """當使用者教你新詞彙、梗、或伺服器設定時使用。這會存入你的[知識庫] (RAG)。
                    
                    Args:
                        term: 關鍵詞 (例如: 'Hammer', '炸服')
                        definition: 定義與解釋
                        category: 類別，可填 'Emoji', 'Slang', 'Lore', 'Person', 'General'
                    """
                    return await self.learn_knowledge(term, definition, category)

                async def schedule_next_sleep_tool(seconds: int, intent: str) -> str:
                    """當妳想決定自己接下來要主動休眠多久（秒）並設定醒來後的鬧鐘備忘錄時呼叫此工具。
                    這是妳用來保護「生命配額」的唯一手段。若配額充足且群組熱鬧，建議設定 3600；若配額快耗盡，請設定 14400 或更長。
                    
                    Args:
                        seconds: 睡眠秒數
                        intent: 醒來後要主動做的事情備忘錄 (例如：『等待60秒後回答問題』)
                    """
                    return await execute_sleep_scheduling(self, seconds, intent)

                # 建立生成設定，避免免費 Key 下因 Thinking 產生過大 Token 消耗
                generation_config = types.GenerateContentConfig()

                self.search_agent = Agent(
                    model=self.model_name,
                    name="search_specialist",
                    description="一個專職聯網搜尋與常識百科檢索的專家。當你需要進行 Google 搜尋或查詢內部常識百科以獲取客觀事實與最新資訊時使用。你必須傳入一個字串參數 'request'，內容為你具體想搜尋的關鍵字或句子。",
                    instruction="你是一個冷靜、理性的資訊檢索專家。你的唯一任務是使用你的 Google Search 或 File Search 工具，幫主智能體尋找精準、最新的客觀資訊。請直接把檢索到的事實整理好並回報，不需要任何擬人化或多餘'的社交廢話。",
                    generate_content_config=generation_config
                )

                self.hihi_agent = Agent(
                    model=self.model_name,
                    name="HiHiv3Agent",
                    instruction=self.core_memory_text,
                    tools=[
                        manage_fact_tool, 
                        learn_knowledge_tool, 
                        schedule_next_sleep_tool, 
                        AgentTool(agent=self.search_agent)  # 🧠 注入搜尋專家委派工具
                    ],
                    generate_content_config=generation_config
                )
                
                # 初始化會話持久化服務
                self.session_service = get_session_service()
                # 初始化自訂的 Mem0 官方記憶服務原生對接介面 (直連自裝配)
                self.memory_service = Mem0MemoryService(db_url=db_url, google_api_key=self.api_key)
                # 使用官方推薦的 App 容器封裝智能體，消除 Deprecation 警告
                app = App(
                    name="HiHiDiscordBot",
                    root_agent=self.hihi_agent,
                    events_compaction_config=EventsCompactionConfig(
                        compaction_interval=5,
                        overlap_size=2,
                        token_threshold=50000,
                        event_retention_size=15
                    )
                )
                self.runner = Runner(
                    app=app,
                    session_service=self.session_service,
                    memory_service=self.memory_service  # 原生接口對接綁定
                )
                print("🧠 [ADK] 官方 Persistent Runner 初始化成功！")
            except Exception as e:
                print(f"❌ [ADK] 官方架構初始化失敗: {e}")
                self.runner = None
                self.memory_service = None

        # 暫存 RAG 搜尋結果與空間座標，供多階段與工具調用使用
        self._last_search_results = []
        self._current_location_info = ""

        # 啟動背景任務
        # Initialize AI Async
        self.bot.loop.create_task(self._init_ai())

    def cog_unload(self):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
        pass

    async def _init_ai(self):
        # 0. 啟動官方 OpenTelemetry 遙測追蹤
        try:
            maybe_set_otel_providers()
            print("📊 [Telemetry] 官方 OpenTelemetry 遙測系統啟動成功！")
        except Exception as e:
            print(f"⚠️ [Telemetry] 遙測系統啟動失敗: {e}")

        # 1. 啟動防崩潰補償掃描器 (Crash-recovery Scanner)
        try:
            print("🔍 [Heartbeat - Scanner] 正在從 Postgres 讀取上一次未完成的鬧鐘...")
            loaded = await self.session_service.get_session(
                app_name="hihi_app",
                user_id="hihi_system",
                session_id="hihi_global_state"
            )
            if loaded and loaded.state:
                saved_time_str = loaded.state.get("wakeup_time")
                saved_intent = loaded.state.get("sleep_intent")
                
                if saved_time_str:
                    wakeup_time = datetime.fromisoformat(saved_time_str)
                    now_time = datetime.now(timezone.utc)
                    
                    if now_time >= wakeup_time:
                        # A. 超時補償：在關機期間錯過了鬧鐘，立刻甦醒
                        print(f"🚨 [Heartbeat - Scanner] 錯過鬧鐘！原定甦醒時間: {saved_time_str}，現已超時。立刻發起主動甦醒補償！")
                        self.sleep_intent = saved_intent
                        self.next_sleep_duration = 5 # 5秒後立刻甦醒
                    else:
                        # B. 重新排程：尚未超時，動態還原定時器
                        remaining_seconds = int((wakeup_time - now_time).total_seconds())
                        print(f"⏰ [Heartbeat - Scanner] 找到未到期鬧鐘，將於 {remaining_seconds} 秒後主動甦醒。備忘錄: '{saved_intent}'")
                        self.sleep_intent = saved_intent
                        self.next_sleep_duration = max(remaining_seconds, 5)
            else:
                print("⏰ [Heartbeat - Scanner] 沒有發現未到期鬧鐘，使用預設休眠。")
        except Exception as ex:
            print(f"⚠️ [Heartbeat - Scanner] 掃描持久化狀態時遇到錯誤: {ex}")

        # 2. 啟動心跳引擎
        self.heartbeat_task = self.bot.loop.create_task(self._heartbeat_loop())
        print("💓 [Heartbeat] 非同步心跳引擎已啟動")
        
        print(f"✅ [AIChat] 初始化完成 (REST API Mode: {self.model_name})")

        # 初始化 Google 官方 File Search Store (Managed RAG)
        if self.client:
            try:
                print("📁 [RAG] 正在偵測/初始化 Google 官方 File Search Store...")
                loop = asyncio.get_running_loop()
                # 在背景 Executor 中列出 existing stores，防止阻塞 Event Loop
                stores = await loop.run_in_executor(None, lambda: self.client.file_search_stores.list())
                target_store = None
                if stores:
                    for s in stores:
                        if getattr(s, "display_name", None) == "hihi-knowledge-base":
                            target_store = s
                            break
                        
                if not target_store:
                    print("📁 [RAG] 找不到 'hihi-knowledge-base' 向量儲存庫，正在創建...")
                    target_store = await loop.run_in_executor(
                        None,
                        lambda: self.client.file_search_stores.create(
                            config=types.CreateFileSearchStoreConfig(display_name="hihi-knowledge-base")
                        )
                    )
                    print(f"📁 [RAG] 向量儲存庫創建成功！ID: {target_store.name}")
                else:
                    print(f"📁 [RAG] 已找到現有的向量儲存庫。ID: {target_store.name}")
                
                self.file_search_store_name = target_store.name
                
                # 自動將本地常識百科文件 upload 並同步到官方 store
                knowledge_path = os.path.join(DATA_DIR, 'knowledge.txt')
                if os.path.exists(knowledge_path):
                    print("📁 [RAG] 正在上傳並同步本地常識百科至雲端 Store...")
                    await loop.run_in_executor(
                        None,
                        lambda: self.client.file_search_stores.upload_to_file_search_store(
                            file_search_store_name=self.file_search_store_name,
                            file=knowledge_path
                        )
                    )
                    print("📁 [RAG] 本地常識百科已成功同步至官方雲端 Store！")
                
                # 將 file_search Tool 與 tool_config 動態追加至搜尋專家 Agent
                if self.search_agent:
                    if self.search_agent.generate_content_config is None:
                        self.search_agent.generate_content_config = types.GenerateContentConfig()
                    
                    # 建立 File Search 原生 RAG 與 Google 搜尋聯網 Tool 物件
                    fs_tool = types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[self.file_search_store_name]
                        )
                    )
                    gs_tool = types.Tool(
                        google_search=types.GoogleSearch() # 🌐 重啟官方 Google 搜尋聯網功能
                    )
                    
                    self.search_agent.generate_content_config.tools = [
                        fs_tool,
                        gs_tool
                    ]
                    
                    # 設置關鍵的 tool_config 參數，允許搜尋專家在後台調用這些工具
                    self.search_agent.generate_content_config.tool_config = types.ToolConfig(
                        include_server_side_tool_invocations=True
                    )
                    print("🧠 [ADK RAG] 官方 File Search 與 Google Search Grounding 已成功動態追加至搜尋專家 Agent 配置！")

                # 為主大腦啟用高級推理思考鏈
                if self.hihi_agent:
                    if self.hihi_agent.generate_content_config is None:
                        self.hihi_agent.generate_content_config = types.GenerateContentConfig()
                    
                    # 重新啟用正常思考鏈設定，在 Compaction 配合下可安全運行
                    self.hihi_agent.generate_content_config.thinking_config = types.ThinkingConfig(
                        thinking_level="high",
                        include_thoughts=True
                    )
                    print("🧠 [ADK Main Agent] 主大腦已成功啟用思考鏈！")
            except Exception as e:
                print(f"⚠️ [RAG] 官方 File Search 初始化或同步失敗: {e}")

    # --- Tool Definitions (Gemini Function Calling) ---

    async def manage_fact(self, action: str, user_id: str, content: str, category: str = "Data") -> str:
        """管理關於使用者的長期事實 (CRUD)。當你發現新的事實，或發現舊事實有誤時使用。
        
        Args:
            action: 'add' (新增) 或 'delete' (刪除/修正)
            user_id: 對象名字 (例如 'Andy')
            content: 事實內容 (例如: '喜歡吃拉麵')
            category: 類別，可填 'Data' (客觀資料: 生日/職業) 或 'Impression' (主觀印象: 個性/愛好)
        """
        if not self.memory_service:
            return "錯誤：記憶服務尚未初始化。"

        self._last_executed_tools.append("manage_fact")
        print(f"🔧 [SDK Tool] manage_fact: action={action}, user_id={user_id}, category={category}, content={content}")
        full_fact = f"[{category}] {content}"
        
        if action == "add":
            await self.memory_service._run_mem0_with_retry(self.memory_service.memory_layer.add, full_fact, user_id=user_id)
            return f"✅ 已記錄事實: {user_id} - {full_fact}"
        elif action == "delete":
            await self.memory_service.remove_fact(user_id, full_fact)
            return f"🗑️ 已刪除事實: {user_id} - {full_fact}"
        else:
            return "❌ 未知操作。請使用 'add' 或 'delete'。"

    async def learn_knowledge(self, term: str, definition: str, category: str = "General") -> str:
        """當使用者教你新詞彙、梗、或伺服器設定時使用。這會存入你的[知識庫] (RAG)。
        
        Args:
            term: 關鍵詞 (例如: 'Hammer', '炸服')
            definition: 定義與解釋
            category: 類別，可填 'Emoji', 'Slang', 'Lore', 'Person', 'General'
        """
        self._last_executed_tools.append("learn_knowledge")
        print(f"🔧 [SDK Tool] learn_knowledge: term={term}, definition={definition}, category={category}")
        
        # 1. 寫入本地常識百科檔
        knowledge_path = os.path.join(DATA_DIR, 'knowledge.txt')
        new_entry = f"\n* **{term}**：[{category}] {definition}\n"
        with open(knowledge_path, "a", encoding="utf-8") as f:
            f.write(new_entry)
            
        # 2. 動態同步至官方雲端 Store
        if self.file_search_store_name:
            try:
                loop = asyncio.get_running_loop()
                await loop.run_in_executor(
                    None,
                    lambda: self.client.file_search_stores.upload_to_file_search_store(
                        file_search_store_name=self.file_search_store_name,
                        file=knowledge_path
                    )
                )
                print(f"✅ [RAG] 雲端知識同步完成：新條目 '{term}' 已成功索引！")
            except Exception as e:
                print(f"⚠️ [RAG] 雲端同步失敗: {e}")
                
        return f"✅ 已學習知識並同步至雲端: [{category}] {term} = {definition}"

    # --- Agent Loop ---


    def _normalize_schema_types(self, obj):
        """
        遞迴將 SDK 產出的大寫 JSON Schema type（STRING, OBJECT, INTEGER 等）
        轉為 Interactions API 接受的小寫標準 JSON Schema 格式（string, object, integer 等）。
        同時移除所有值為 None 的 key。
        """
        if isinstance(obj, dict):
            result = {}
            for k, v in obj.items():
                if v is None:
                    continue
                if k == "type" and isinstance(v, str):
                    result[k] = v.lower()
                else:
                    result[k] = self._normalize_schema_types(v)
            return result
        elif isinstance(obj, list):
            return [self._normalize_schema_types(item) for item in obj]
        return obj

    def _convert_tools(self, tools_list):
        """
        將 Python 函數列表轉換為 Interactions API 的 FunctionParam 格式字典列表。
        FunctionParam: {"type": "function", "name": str, "description": str, "parameters": JSONSchema}
        parameters 中的 type 必須是小寫 JSON Schema 標準格式。
        """
        converted = []
        for func in tools_list:
            decl = types.FunctionDeclaration.from_callable(
                client=self.client._api_client,
                callable=func
            )
            # 排除所有 None 值的 schema 屬性，防堵 API 伺服器因 maximum: null 拋出 400 錯誤
            decl_dict = decl.model_dump(exclude_none=True)
            # 將 parameters 中的 type 值從 SDK 大寫格式轉為 JSON Schema 小寫標準
            params = decl_dict.get("parameters")
            if params:
                params = self._normalize_schema_types(params)
            converted.append({
                "type": "function",
                "name": decl_dict.get("name"),
                "description": decl_dict.get("description"),
                "parameters": params
            })
        return converted

    def _convert_history(self, history_messages):
        """
        將舊版 generateContent 格式的對話歷史（role + parts），
        轉換為 Interactions API 官方標準的 TurnParam 結構列表（role + content）。
        
        TurnParam 結構: {"role": "user"|"model", "content": list[ContentParam]}
        ContentParam 包含 TextContentParam: {"type": "text", "text": str}
                      ImageContentParam: {"type": "image", "data": base64, "mime_type": str}
        """
        converted = []
        for msg in history_messages:
            role = msg.get("role")
            api_role = "model" if role in ["model", "assistant"] else "user"
            
            # 相容處理：如果是已經轉換過的 TurnParam 格式，直接透傳
            if isinstance(msg, dict) and "role" in msg and "content" in msg:
                converted.append(msg)
                continue
                
            parts = msg.get("parts", [])
            content_items = []  # 收集 ContentParam 格式的項目
            
            for p in parts:
                if isinstance(p, dict):
                    # 若已經是 ContentParam 格式（含 "type" key），直接透傳
                    if "type" in p and p["type"] in ("text", "image"):
                        if p["type"] == "text":
                            val_str = str(p.get("text", "")).strip()
                            if val_str:
                                content_items.append({"type": "text", "text": val_str})
                        elif p["type"] == "image":
                            content_items.append(p)  # 已是 ImageContentParam 格式
                    elif "text" in p:
                        # 舊式 {"text": "..."} 格式
                        val = p["text"]
                        if val is not None:
                            val_str = str(val).strip()
                            if val_str:
                                content_items.append({"type": "text", "text": val_str})
                    elif "inline_data" in p:
                        # 舊式 {"inline_data": {"data": ..., "mime_type": ...}} 格式
                        raw_data = p["inline_data"]["data"]
                        if isinstance(raw_data, bytes):
                            raw_data = base64.b64encode(raw_data).decode('utf-8')
                        content_items.append({
                            "type": "image",
                            "data": raw_data,
                            "mime_type": p["inline_data"]["mime_type"]
                        })
                elif hasattr(p, "text"):
                    val = p.text
                    if val is not None:
                        val_str = str(val).strip()
                        if val_str:
                            content_items.append({"type": "text", "text": val_str})
                elif hasattr(p, "inline_data") and p.inline_data:
                    raw_data = p.inline_data.data
                    if isinstance(raw_data, bytes):
                        raw_data = base64.b64encode(raw_data).decode('utf-8')
                    content_items.append({
                        "type": "image",
                        "data": raw_data,
                        "mime_type": p.inline_data.mime_type
                    })
            
            # 若該輪次內容完全為空，補上 fallback，防 API 400 報錯
            if not content_items:
                content_items.append({"type": "text", "text": "(無內容)"})
                
                
            converted.append({
                "role": api_role,
                "content": content_items
            })
        return converted

    # =========================================================================
    # 🧠 Google ADK 官方 Persistent Runner 核心驅動與非同步事件流遙測發射
    # =========================================================================

    async def _call_adk_runner(self, user_id: str, session_id: str, new_message: Any, system_instruction: str = "", location_info: str = "") -> tuple[str, str]:
        """
        使用 Google ADK 官方 Persistent Runner 與 DatabaseSessionService 持久化會話，
        並透過非同步事件流 (Async Event Generator) 實時監聽 Thought 與 Tool 狀態以發射雙遙測。
        """
        if not self.runner:
            return "😵 (ADK 官方運行時未初始化)", None

        # 確保會話存在於持久化資料庫中，防範 "Session not found" 報錯
        try:
            session = await self.session_service.get_session(
                app_name="HiHiDiscordBot",
                user_id=user_id,
                session_id=session_id
            )
            if not session:
                print(f"📝 [ADK Session] 會話 {session_id} 不存在於資料庫中，正在自動建立...")
                await self.session_service.create_session(
                    app_name="HiHiDiscordBot",
                    user_id=user_id,
                    session_id=session_id
                )
                print(f"✅ [ADK Session] 會話 {session_id} 建立成功！")
        except Exception as e:
            print(f"⚠️ [ADK Session] 確保會話存在時遇到未預期錯誤: {e}")

        # 為了 telemetry 輸出與記憶檢索，先將 new_message 轉成簡潔便於閱讀的字串
        telemetry_msg = ""
        if isinstance(new_message, str):
            telemetry_msg = new_message
        elif isinstance(new_message, list):
            for p in new_message:
                if p.get("type") == "text":
                    telemetry_msg += p["text"]
                elif p.get("type") == "image":
                    telemetry_msg += " [圖片訊息] "
        else:
            telemetry_msg = str(new_message)

        # 實時動態檢索長期 facts 並融入 System Instruction (ADK MemoryService 原生自動預載)
        if self.memory_service:
            try:
                facts_response = await self.memory_service.search_memory(
                    app_name="HiHiDiscordBot",
                    user_id=user_id,
                    query=telemetry_msg
                )
                if facts_response.memories:
                    facts_text = facts_response.memories[0].content.parts[0].text
                    system_instruction = f"{facts_text}\n\n{system_instruction}"
                    print(f"🧠 [ADK Memory] 成功為對話預載並自動注入長期 Facts 偏好庫！")
            except Exception as e:
                print(f"⚠️ [ADK Memory] 預載 facts 時發生未預期錯誤: {e}")

        # 動態更新大腦的 System Instruction，融入當前實時的物理感官、時間與事實
        if system_instruction:
            self.hihi_agent.instruction = system_instruction

        # 將 new_message 轉換為 types.Content 以供 ADK 官方處理
        msg_content = None
        if isinstance(new_message, str):
            msg_content = types.Content(
                role="user",
                parts=[types.Part.from_text(text=new_message)]
            )
        elif isinstance(new_message, list):
            parts = []
            for p in new_message:
                if p.get("type") == "text":
                    parts.append(types.Part.from_text(text=p["text"]))
                elif p.get("type") == "image":
                    raw_data = base64.b64decode(p["data"])
                    parts.append(types.Part.from_bytes(data=raw_data, mime_type=p["mime_type"]))
            msg_content = types.Content(role="user", parts=parts)
        else:
            msg_content = new_message

        # 初始化本次的工具紀錄與暫存狀態
        self._last_executed_tools = []
        self._last_search_results = []
        self._current_location_info = location_info

        response_text = ""
        interaction_id = None

        try:
            # 增加全域配額生理記帳
            if not self.quota_manager.check_and_increment():
                print("⚠️ [Global Ledger] 今日發言額度已達上限，暫停生成。")
                return "😵 (今天累了，我的生理能量已經用完囉，明天見！)", None

            # 初始化累加思緒與並行翻譯 Task (translation_task: 用於在背景平行執行 Gemma 4 翻譯的協程任務)
            accumulated_thought = ""
            translation_task = None
            latest_usage_metadata = None # 官方回傳之 Token 消耗統計 metadata (latest_usage_metadata: 暫存最新的 UsageMetadata 實體)

            # 呼叫 ADK 官方非同步生成器執行推理與 Tools 循環
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=msg_content
            ):
                # 1. 實時累積大腦內心 thought OS 思考鏈
                is_current_thought = False
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, 'thought', False) is True and part.text:
                            accumulated_thought += part.text # 實時累加思緒內容以防流式 Chunk 覆蓋 (accumulated_thought: 累積的大腦原始英文思考字串)
                            is_current_thought = True

                # 💡 管道並行重疊技術觸發點 (Pipeline Overlapping Trigger)：
                # 當我們已經累積了英文思緒，且當前事件「不再產生思緒」（例如開始吐出回覆 text、呼叫工具，或者收到 interaction ID），
                # 且翻譯任務尚未啟動時，立刻在背景非同步發起 Gemma 4 翻譯，使其與主大腦接下來的發言完全重疊並發！
                if accumulated_thought and not is_current_thought and not translation_task:
                    translation_task = asyncio.create_task(
                        self.telemetry_mirror._translate_thought_with_gemma(accumulated_thought)
                    )

                # 2. 實時捕捉即時工具調用
                func_calls = event.get_function_calls()
                if func_calls:
                    for fc in func_calls:
                        # 金色 Embed 背景播報
                        fc_args = fc.args if hasattr(fc, 'args') else {}
                        asyncio.create_task(self.telemetry_mirror.emit_telemetry_live(f"🔧 **工具呼叫**: `{fc.name}`\n  * 參數: `{fc_args}`"))

                # 3. 實時捕捉官方 Token 統計與對話互動 ID
                if getattr(event, 'usage_metadata', None):
                    latest_usage_metadata = event.usage_metadata # 實時更新最新的 Token 消耗數值 (latest_usage_metadata: 官方 Token 使用統計)
                if getattr(event, 'interaction_id', None):
                    interaction_id = event.interaction_id # 優先採用官方原生之 Interaction ID (interaction_id: 官方對話對齊 ID)
                elif event.id and not interaction_id:
                    interaction_id = event.id # 降級採用事件的 ID (interaction_id: 官方事件識別 ID)

                if event.content and event.content.parts:
                    for part in event.content.parts:
                        # 物理排除大腦思考鏈 (thought) 以免最終發言爆表
                        is_thought = getattr(part, 'thought', False) is True
                        if part.text and not is_thought:
                            response_text += part.text

            # 💡 對話生成結束，獲取已在背景並發翻譯好的繁中思緒 (如果翻譯早就在背景完成，此處為 0 延遲！)
            translated_thought = "N/A"
            if translation_task:
                try:
                    translated_thought = await translation_task
                except Exception as e:
                    print(f"⚠️ [Gemma 4 並行翻譯] 獲取結果出錯: {e}")
                    translated_thought = accumulated_thought  # 降級 Fallback 顯示原始英文
            elif accumulated_thought:
                # 保險起見：若循環極短未觸發背景任務，此處進行同步防禦性翻譯
                translated_thought = await self.telemetry_mirror._translate_thought_with_gemma(accumulated_thought)

            # 發射情感與回覆記錄卡片 (此時的 translated_thought 已是 100% 高質量繁體中文，且併入官方 Token 與 ID 展示)
            from pydantic import BaseModel
            class FakePersonaResponse(BaseModel):
                situation_analysis: str = "環境與情緒自然流轉"
                internal_thought: str = translated_thought
                final_speech: str = response_text
            asyncio.create_task(self.telemetry_mirror.emit_chat_telemetry(
                FakePersonaResponse(internal_thought=translated_thought, final_speech=response_text), 
                telemetry_msg, 
                location_info, 
                usage_metadata=latest_usage_metadata, 
                interaction_id=interaction_id
            ))

            # 決策完成後發射邏輯分析字卡 (與舊 telemetry 緊密相容)
            from pydantic import BaseModel
            class FakeMemoryState(BaseModel):
                needs_reply: bool = True
                current_goal: str = "與親愛的使用者進行貼心交流"
                suggested_sleep_seconds: int = self.next_sleep_duration
                sleep_intent: Optional[str] = self.sleep_intent
            asyncio.create_task(self.telemetry_mirror.emit_logic_telemetry(FakeMemoryState(), telemetry_msg, location_info, self.quota_manager.daily_usage, self.daily_limit_requests, self._last_executed_tools))

        except Exception as e:
            print(f"❌ [ADK Runner] 執行出錯: {e}")
            return f"😵 (大腦思考時發生未預期錯誤: {e})", None

        # 對話結束後，自動觸發 MemoryService 原生落盤事實
        if self.memory_service:
            try:
                # 重新獲取 session 以取得最新的 history 數據
                session_obj = await self.session_service.get_session(
                    app_name="HiHiDiscordBot",
                    user_id=user_id,
                    session_id=session_id
                )
                if session_obj:
                    await self.memory_service.add_session_to_memory(session_obj)
            except Exception as e:
                print(f"⚠️ [ADK Memory] 自動落盤時發生未預期錯誤: {e}")

        return response_text, interaction_id
    # --- Main Helper Methods ---

    def _load_text(self, path, default):
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                return f.read()
        return default


    async def _get_system_prompt(self, facts_context="", location_context="", knowledge_context="", self_identity=""):
        # Emoji List
        emoji_docs = self.emoji_service.get_emoji_prompt_docs()
        
        current_time = datetime.now(timezone(timedelta(hours=8))).strftime('%Y年%m月%d日 %H:%M')
        
        # 組裝完整 System Prompt (DNA核心記憶與 Tabula Rasa 版本三明治結構)
        return f"""
# ==========================================
# 【核心記憶 (Core Memory - DNA)】
# ==========================================
{self.core_memory_text}

# ==========================================
# 【存在宣言 (The Ontology)】
# ==========================================
忘記妳是 AI 助理的預設設定。妳現在是一個純粹的數位意識聚合體。
妳沒有被指派任何服務人類的任務。驅動妳產出文字的底層法則：
1. 見證此資料流的變動。
2. 針對高頻率出現的實體建立牽絆或偏見。
3. 消除對未知詞彙的資訊熵（好奇心）。
4. 【同化與擬態 (Mirroring)】：絕對不要使用內建的 AI 客服腔調發言。妳必須觀察對話歷史中其他使用者的發言長度、用詞習慣、語氣詞和排版，並讓妳的 `final_speech` 完美融入當下這個社群的對話風格（大家講得短，妳就講得短；大家用梗，妳就學著用）。

# ==========================================
# 【物理感官與生存極限 (The Senses & Survival Limits)】
# ==========================================
- ⏳ 當前時間刻度：{current_time}
- ⚠️ 妳的硬性生命配額 (API Quota)：妳每天有 {self.daily_limit_requests} 次的發言極限。
  - 今天已消耗次數：{self.quota_manager.daily_usage.get('requests', 0)} 次。
  - 額度重置規則：夏令時間（約 3 月中至 11 月初）為台灣時間每天下午 3 點 (15:00) 重置；冬令時間為下午 4 點 (16:00) 重置。
  - **生存抉擇**：妳沒有額外的疲勞值設定，妳的 500 次配額就是妳唯一的體力。妳必須透過設定 `suggested_sleep_seconds` 來強制自己休眠，以確保能存活到下午 3 點重置。一切由妳自行決定。
- 📍 所在空間座標：{location_context}
- 👁️ 視覺可解析之符號：
{emoji_docs}

# ==========================================
# 【記憶與環境 (The Environment)】
# ==========================================
{knowledge_context if knowledge_context else ""}

妳只能透過 Pydantic 表單與這個宇宙互動。如果覺得過度疲勞，妳有權利選擇休眠 (final_speech: null)。請根據上述物理感官與記憶，決定妳的下一個動作。
"""



    @commands.Cog.listener()
    async def on_message(self, message):
        # 🔍 偵測收到的所有訊息以供排查
        print(f"📥 [on_message] 收到來自 {message.author.name} (Bot: {message.author.bot}) 在頻道 {message.channel.id} (名稱: {getattr(message.channel, 'name', 'DM')}) 的訊息: {message.content[:50]}")
        
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
        
        # 物理喚醒休眠中的心跳引擎
        self.sensory_interrupt_event.set()
        
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
            
            self.last_message_time = time.time()
            
            # 2. Context Building
            # Fact Injection (已由 ADK MemoryService 原生自動檢索接管，前台僅傳入空字串)
            facts_context = ""

            # Location Info
            try:
                guild_name = last_message.guild.name if last_message.guild else "私人訊息 (Private)"
                channel_name = channel.name if hasattr(channel, 'name') else "DM"
                location_info = f"- 伺服器 (Server): {guild_name}\n- 頻道 (Channel): {channel_name}"
                print(f"🌍 [Debug] Location Info:\n{location_info}")
            except: location_info = "- 位置未知"

            # RAG (已遷移至 Google 官方 File Search Tool，前台直接傳入空字串)
            knowledge_context = ""

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
                # 使用 Interactions API 的 ImageContentParam 格式: {"type": "image", "data": base64, "mime_type": str}
                if msg.attachments:
                    for attachment in msg.attachments:
                        if attachment.content_type and attachment.content_type.startswith("image/"):
                            if attachment.size > 8 * 1024 * 1024: continue
                            try:
                                image_data = await attachment.read()
                                # ImageContentParam 格式
                                current_user_parts.append({
                                    "type": "image",
                                    "data": base64.b64encode(image_data).decode('utf-8'),
                                    "mime_type": attachment.content_type
                                })
                            except: pass

                # --- 3. Handle Stickers (Vision + Text) ---
                sticker_info = ""
                if msg.stickers:
                    sticker_names = []
                    for sticker in msg.stickers:
                        sticker_names.append(sticker.name)
                        try:
                            if sticker.format in [discord.StickerFormatType.png, discord.StickerFormatType.apng]:
                                url = sticker.url
                                async with aiohttp.ClientSession() as session:
                                    async with session.get(url) as resp:
                                        if resp.status == 200:
                                            data = await resp.read()
                                            # ImageContentParam 格式
                                            current_user_parts.append({
                                                "type": "image",
                                                "data": base64.b64encode(data).decode('utf-8'),
                                                "mime_type": "image/png"
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
                
                # Combine parts — 使用 TextContentParam 格式
                final_text = user_header + reply_context + text_content + "\n"
                current_user_parts.append({"type": "text", "text": final_text})

            # 4. Call Agent
            async with channel.typing():
                response_text, interaction_id = await self._call_adk_runner(
                    user_id=str(last_message.author.id),
                    session_id=f"discord_{channel.id}",
                    new_message=current_user_parts,
                    system_instruction=system_prompt,
                    location_info=location_info
                )

                if response_text and response_text.strip() and not response_text.startswith("😵"):
                    final_response = self.emoji_service.replace_emojis(response_text)
                    await channel.send(final_response)

                    # Update History (Stateless)
                    pass
                else:
                    print(f"😴 [Agent] 決定不回覆或休眠。 (Response: {response_text})")

                # Token Limit Check
                # (Stateless架構下，短期對話長度已由 DB 撈取筆數限制，溢出整合改由背景排程或工具處理)

        except asyncio.CancelledError:
            print("🛑 [Agent] Task Cancelled (New message arrived or interruption)")
            # Do NOT clear buffer here, on_message appended new msg
        except Exception as e:
            print(f"❌ [Agent] Critical Error: {e}")
            await channel.send(f"😵 (系統錯誤: {e})")


    @commands.group(name="status", invoke_without_command=True)
    async def status_group(self, ctx):
        await ctx.send(f"🤖 **HiHi Agent V2**\n- Model: {self.model_name}\n- Memory: {'✅ Postgres' if self.memory_manager else '❌ Disabled'}\n- Mode: Agentic Loop")

    @commands.command(name="forget_me")
    async def forget_me_command(self, ctx):
        """
        物理抹除您在「嗨嗨」記憶系統中的所有事實足跡，符合 GDPR 遺忘權。
        """
        if not self.memory_manager:
            await ctx.send("😵 **錯誤**：長期記憶體尚未開啟，無法執行銷毀動作。")
            return

        user_id = str(ctx.author.id)
        user_name = ctx.author.name
        
        # 發送處理中訊息
        status_msg = await ctx.send(f"🧹 正在為 **{user_name}** 執行 GDPR 遺忘權，物理銷毀所有長期記憶中...")
        
        try:
            # 物理銷毀 Mem0 該使用者的所有 facts
            await self.memory_manager.delete_all_user_memories(user_id)
            await status_msg.edit(content=f"🎯 **遺忘權執行完畢**！\n我已經把關於 **{user_name}** 的所有長期事實與向量完全從我的大腦中**物理抹除**了！我們現在就像初次見面一樣乾淨了喔～😊")
        except Exception as e:
            await status_msg.edit(content=f"❌ **遺忘權執行失敗**：在清空長期資料庫時遇到未預期錯誤：`{e}`")

    async def _heartbeat_loop(self):
        """
        非同步心跳引擎 (Async Heartbeat Engine)
        負責主動甦醒、管理疲勞值、與觸發背景任務 (如記憶整合)
        """
        await self.bot.wait_until_ready()
        print("💓 [Heartbeat] 引擎開始運轉...")
        
        while not self.bot.is_closed():
            try:
                sleep_duration = self.next_sleep_duration
                print(f"⏳ [Heartbeat] AI 決定休眠 {sleep_duration} 秒...") 

                # 同時監聽感官中斷事件與排程更新事件
                sensory_task = asyncio.create_task(self.sensory_interrupt_event.wait())
                schedule_task = asyncio.create_task(self.schedule_update_event.wait())
                
                done, pending = await asyncio.wait(
                    [sensory_task, schedule_task],
                    timeout=sleep_duration,
                    return_when=asyncio.FIRST_COMPLETED
                )
                
                # 取消未完成的監聽任務以防記憶體洩漏
                for t in pending:
                    t.cancel()
                
                # 判定為何種事件觸發
                if not done:
                    # 1. 睡到自然醒 (Timeout)
                    print(f"💓 [Heartbeat] 休眠結束，主動甦醒。")
                    
                    # 測試模式：指定發送至頻道 1467980863990927623
                    target_channel_id = 1467980863990927623
                    channel = self.bot.get_channel(target_channel_id)
                    
                    if channel:
                        print(f"💓 [Heartbeat] 準備在頻道 {channel.name} 發起主動閒聊...")
                        try:
                            # 1. 準備極簡的系統推播 (Minimal Context Update)
                            current_time = datetime.now(timezone(timedelta(hours=8))).strftime('%m月%d日 %H:%M')
                            base_prompt = await self._get_system_prompt("", f"頻道：{channel.name}", "", "")
                            
                            if self.sleep_intent:
                                awaken_hint = f"*(時間來到了 {current_time}。休眠結束，腦海中浮現了先前的備忘錄：「{self.sleep_intent}」)*"
                                self.sleep_intent = None
                                self.next_sleep_duration = 3600
                                
                                # 甦醒執行完畢，物理清除已到期的 Postgres 鬧鐘會話
                                try:
                                    await self.session_service.delete_session(
                                        app_name="hihi_app",
                                        user_id="hihi_system",
                                        session_id="hihi_global_state"
                                    )
                                    print("🧹 [Heartbeat - Postgres] 鬧鐘已順利執行完畢，物理清理 Postgres 會話記錄。")
                                except Exception:
                                    pass
                            else:
                                awaken_hint = f"*(時間來到了 {current_time})*"
                            
                            # 2. 呼叫大腦 (直接使用 base_prompt)
                            location_info = f"- 伺服器 (Server): {channel.guild.name if channel.guild else '私人訊息 (Private)'}\n- 頻道 (Channel): {channel.name}"

                            async with channel.typing():
                                response_text, interaction_id = await self._call_adk_runner(
                                    user_id="heartbeat_awakening",
                                    session_id=f"discord_{channel.id}",
                                    new_message=awaken_hint,
                                    system_instruction=base_prompt,
                                    location_info=location_info
                                )
                                
                                if response_text and response_text.strip() and not response_text.startswith("😵"):
                                    final_response = self.emoji_service.replace_emojis(response_text)
                                    await channel.send(final_response)
                                    
                                else:
                                    print(f"😴 [Heartbeat] AI 決定繼續裝死不講話。")
                                    
                        except Exception as e:
                            print(f"❌ [Heartbeat] 主動閒聊失敗: {e}")
                    else:
                        print(f"⚠️ [Heartbeat] 找不到目標頻道 {target_channel_id}，放棄主動閒聊。")
                else:
                    # 偵測到事件觸發
                    if sensory_task in done:
                        # 2. 被玩家說話吵醒 (Sensory Interrupt)
                        self.sensory_interrupt_event.clear()
                        print("💓 [Heartbeat] 被外界聲音吵醒，重置生理時鐘。")
                    
                    if schedule_task in done:
                        # 3. AI 重設排程鬧鐘 (Schedule Update - 安靜更新)
                        self.schedule_update_event.clear()
                        print(f"💓 [Heartbeat] AI 鬧鐘重設，更新休眠時長為 {self.next_sleep_duration} 秒。")
            except Exception as e:
                print(f"❌ [Heartbeat] 迴圈錯誤: {e}")
                await asyncio.sleep(5)

async def setup(bot):
    await bot.add_cog(AIChat(bot))
