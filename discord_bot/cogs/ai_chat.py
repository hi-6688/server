
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
from bs4 import BeautifulSoup
import re
from youtube_comment_downloader import YoutubeCommentDownloader, SORT_BY_POPULAR
import itertools
import hashlib
from google import genai
from google.genai import types
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions.database_session_service import DatabaseSessionService


# --- 設定檔路徑 ---
BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
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
        # 預設使用 gemini-3.1-flash-lite
        self.model_name = os.getenv("AI_MODEL_NAME", "gemini-3.1-flash-lite").split('#')[0].strip()
        
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

        # 載入靜態/設定檔
        self.daily_limit_requests = 500
        self.usage_file = os.path.join(DATA_DIR, 'daily_usage.json')
        self.daily_usage = self._load_json(self.usage_file, {'date': '', 'requests': 0, 'tokens': 0})
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
            self.memory_manager = MemoryManager(db_url, self.api_key, api_quota_callback=self._increment_usage)
            print("🧠 [Memory] RAG 系統已初始化 (v3.0 - 連線池模式)")
        else:
            print("❌ [Memory] CRITICAL ERROR: DATABASE_URL not set. Memory disabled.")
            self.memory_manager = None

        # 初始化 Google ADK Agent 與 DatabaseSessionService 持久化會話 Runner
        self.runner = None
        if db_url and self.api_key:
            try:
                # 定義長期事實與學習工具 (讓 ADK 自動分析 Schema，完美掛載)
                async def save_memory_tool(user_name: str, content: str, importance: int = 5) -> str:
                    """當你覺得這段對話包含重要的長期資訊、個人喜好、或值得記住的觀察時使用。不要記瑣碎的事。
                    
                    Args:
                        user_name: 對話者的名字
                        content: 要記住的具體內容 (例如: 'Andy 喜歡吃拉麵')
                        importance: 重要程度 (1-10)
                    """
                    return await self.save_memory(user_name, content, importance)

                async def manage_fact_tool(action: str, user_id: str, content: str, category: str = "Data") -> str:
                    """管理關於使用者的長期事實 (CRUD)。當你發現新的事實，或發現舊事實有誤時使用。
                    
                    Args:
                        action: 'add' (新增) 或 'delete' (刪除/修正)
                        user_id: 對象名字 (例如 'Andy')
                        content: 事實內容 (例如: '喜歡吃拉麵')
                        category: 類別，可填 'Data' (客觀資料: 生日/職業) 或 'Impression' (主觀印象: 個性/愛好)
                    """
                    return await self.manage_fact(action, user_id, content, category)

                async def search_memory_tool(query: str) -> str:
                    """當你需要回顧過去的對話、事實、或搜尋特定主題時使用。
                    
                    Args:
                        query: 搜尋關鍵字或問題
                    """
                    return await self.search_memory(query)

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
                    self.next_sleep_duration = seconds
                    self.sleep_intent = intent
                    self.schedule_update_event.set()
                    print(f"💤 [ADK Tool - Sleep] AI 主動設定生理時鐘: 休眠 {seconds} 秒，備忘錄: '{intent}'")
                    return f"✅ 已成功為您排程下一次生理休眠 {seconds} 秒，備忘錄已設定。"

                # 建立 Agent (掛載工具，以 DNA 核心記憶作為 System Instruction)
                self.hihi_agent = Agent(
                    model=self.model_name,
                    name="HiHiv3Agent",
                    instruction=self.core_memory_text,
                    tools=[save_memory_tool, manage_fact_tool, search_memory_tool, learn_knowledge_tool, schedule_next_sleep_tool]
                )
                
                # 處理 SQLAlchemy asyncpg 要求使用 postgresql+asyncpg:// 協議的問題
                adk_db_url = db_url
                if adk_db_url.startswith("postgres://"):
                    adk_db_url = adk_db_url.replace("postgres://", "postgresql+asyncpg://", 1)
                elif adk_db_url.startswith("postgresql://"):
                    adk_db_url = adk_db_url.replace("postgresql://", "postgresql+asyncpg://", 1)

                # asyncpg 不支持 sslmode 引數，直接將其從 URL 中移除以防連線崩潰
                if "?" in adk_db_url:
                    base_url, query_str = adk_db_url.split("?", 1)
                    params = [p for p in query_str.split("&") if not p.startswith("sslmode=")]
                    adk_db_url = f"{base_url}?{'&'.join(params)}" if params else base_url

                # 初始化會話持久化服務與 Runner
                self.session_service = DatabaseSessionService(db_url=adk_db_url)
                self.runner = Runner(
                    app_name="HiHiDiscordBot",
                    agent=self.hihi_agent,
                    session_service=self.session_service
                )
                print("🧠 [ADK] 官方 Persistent Runner 初始化成功！")
            except Exception as e:
                print(f"❌ [ADK] 官方架構初始化失敗: {e}")
                self.runner = None

        # 暫存 RAG 搜尋結果與空間座標，供多階段與工具調用使用
        self._last_search_results = []
        self._current_location_info = ""

        # 啟動背景任務
        # Initialize AI Async
        self.bot.loop.create_task(self._init_ai())

    def cog_unload(self):
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
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
        
        print(f"✅ [AIChat] 初始化完成 (REST API Mode: {self.model_name})")
        
        # 啟動心跳引擎
        self.heartbeat_task = self.bot.loop.create_task(self._heartbeat_loop())
        print("💓 [Heartbeat] 非同步心跳引擎已啟動")

    # --- Tool Definitions (Gemini Function Calling) ---

    async def save_memory(self, user_name: str, content: str, importance: int = 5) -> str:
        """當你覺得這段對話包含重要的長期資訊、個人喜好、或值得記住的觀察時使用。不要記瑣碎的事。
        
        Args:
            user_name: 對話者的名字
            content: 要記住的具體內容 (例如: 'Andy 喜歡吃拉麵')
            importance: 重要程度 (1-10)
        """
        if not self.memory_manager:
            return "錯誤：記憶管理器尚未初始化。"

        self._last_executed_tools.append("save_memory")
        print(f"🔧 [SDK Tool] save_memory: user_name={user_name}, content={content}, importance={importance}")
        loc_meta = self._current_location_info.replace('\n', ' | ') if self._current_location_info else "位置未知"
        await self.memory_manager.add_memory(user_name, content, importance, metadata={"location": loc_meta})
        return f"✅ 已儲存記憶: {content}"

    async def manage_fact(self, action: str, user_id: str, content: str, category: str = "Data") -> str:
        """管理關於使用者的長期事實 (CRUD)。當你發現新的事實，或發現舊事實有誤時使用。
        
        Args:
            action: 'add' (新增) 或 'delete' (刪除/修正)
            user_id: 對象名字 (例如 'Andy')
            content: 事實內容 (例如: '喜歡吃拉麵')
            category: 類別，可填 'Data' (客觀資料: 生日/職業) 或 'Impression' (主觀印象: 個性/愛好)
        """
        if not self.memory_manager:
            return "錯誤：記憶管理器尚未初始化。"

        self._last_executed_tools.append("manage_fact")
        print(f"🔧 [SDK Tool] manage_fact: action={action}, user_id={user_id}, category={category}, content={content}")
        full_fact = f"[{category}] {content}"
        
        if action == "add":
            await self.memory_manager.add_fact(user_id, full_fact)
            return f"✅ 已記錄事實: {user_id} - {full_fact}"
        elif action == "delete":
            await self.memory_manager.remove_fact(user_id, full_fact)
            return f"🗑️ 已刪除事實: {user_id} - {full_fact}"
        else:
            return "❌ 未知操作。請使用 'add' 或 'delete'。"

    async def search_memory(self, query: str) -> str:
        """當你需要回憶過去的對話、事實、或搜尋特定主題時使用。
        
        Args:
            query: 搜尋關鍵字或問題
        """
        if not self.memory_manager:
            return "錯誤：記憶管理器尚未初始化。"

        self._last_executed_tools.append("search_memory")
        print(f"🔧 [SDK Tool] search_memory: query={query}")
        results = await self.memory_manager.search_memory(query)
        if not results:
            return "沒有找到相關記憶。"
        
        res_blocks = []
        for r in results:
            date_str = r['created_at'].strftime('%Y-%m-%d %H:%M')
            block = f"📍 【記憶標籤】 ({date_str}) {r['user_name']}: {r['content']}\n"
            if r.get('raw_context'):
                block += "   📜 當時的對話現場 (原文重現):\n"
                for ctx in r['raw_context']:
                    block += f"      {ctx}\n"
            res_blocks.append(block)
        
        result_str = f"🔍搜尋結果:\n" + "\n".join(res_blocks)
        self._last_search_results.append(result_str)
        return result_str

    async def learn_knowledge(self, term: str, definition: str, category: str = "General") -> str:
        """當使用者教你新詞彙、梗、或伺服器設定時使用。這會存入你的[知識庫] (RAG)。
        
        Args:
            term: 關鍵詞 (例如: 'Hammer', '炸服')
            definition: 定義與解釋
            category: 類別，可填 'Emoji', 'Slang', 'Lore', 'Person', 'General'
        """
        if not self.memory_manager:
            return "錯誤：記憶管理器尚未初始化。"

        self._last_executed_tools.append("learn_knowledge")
        print(f"🔧 [SDK Tool] learn_knowledge: term={term}, definition={definition}, category={category}")
        await self.memory_manager.add_knowledge(term, definition, category)
        return f"✅ 已學習知識: [{category}] {term} = {definition}"

    # --- Agent Loop ---


    async def _emit_logic_telemetry(self, memory_state, trigger_text, location_info=""):
        if not self.inner_world_channel_id: 
            return
        channel = self.bot.get_channel(self.inner_world_channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.inner_world_channel_id)
            except Exception as e:
                print(f"⚠️ 邏輯遙測失敗：找不到頻道 ({self.inner_world_channel_id}): {e}")
                return
        
        try:
            embed = discord.Embed(title="🧠 邏輯分析", color=0x3a86ff, timestamp=datetime.now(timezone(timedelta(hours=8))))
            
            # 1. 空間座標與觸發源 (並排 inline=True)
            short_trigger = trigger_text[:100] + "..." if len(trigger_text) > 100 else trigger_text
            embed.add_field(name="📍 空間座標", value=f"```\n{location_info.strip()}\n```" if location_info else "```位置未知```", inline=True)
            embed.add_field(name="🎯 觸發源", value=f"```\n{short_trigger}\n```", inline=True)
            
            # 2. 生存指標與生理調控
            req = self.daily_usage.get('requests', 0)
            limit = self.daily_limit_requests
            pct = (req / limit) * 100 if limit > 0 else 0
            color_emoji = "🟢"
            if pct > 60: color_emoji = "🟡"
            if pct > 90: color_emoji = "🔴"
            
            vitals = f"{color_emoji} 消耗配額: **{req} / {limit}** ({pct:.1f}%)\n"
            vitals += f"💤 自主休眠決策: **{memory_state.suggested_sleep_seconds} 秒**"
            if memory_state.sleep_intent:
                vitals += f"\n⏰ 鬧鐘備忘錄: `{memory_state.sleep_intent}`"
            embed.add_field(name="⚡ 生存指標與生理調控", value=vitals, inline=False)
            
            # 3. 物理行動決策
            executed_tools = getattr(self, '_last_executed_tools', [])
            action_text = f"**🎯 當前目標**: {memory_state.current_goal}\n"
            if executed_tools:
                action_text += "**🔧 物理行動細節**:\n" + "\n".join([f"- {tool}" for tool in executed_tools])
            else:
                action_text += "**🤐 拒絕執行工具 (無呼叫)**"
            embed.add_field(name="🚀 物理行動決策", value=action_text, inline=False)
            
            await channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ 邏輯遙測發送錯誤: {e}")

    async def _emit_chat_telemetry(self, persona_response, trigger_text, location_info=""):
        if not self.inner_world_channel_id: 
            return
        channel = self.bot.get_channel(self.inner_world_channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.inner_world_channel_id)
            except Exception as e:
                print(f"⚠️ 情感遙測失敗：找不到頻道 ({self.inner_world_channel_id}): {e}")
                return
                
        try:
            embed = discord.Embed(title="👁️ 發言決策", color=0xff006e, timestamp=datetime.now(timezone(timedelta(hours=8))))
            
            # 1. 情況分析
            sit = persona_response.situation_analysis if persona_response.situation_analysis else "N/A"
            embed.add_field(name="👁️ 外界情境分析", value=sit, inline=False)
            
            # 2. 內心 OS (使用高雅的 Discord 引言 Markdown 格式)
            os_text = persona_response.internal_thought if persona_response.internal_thought else "N/A"
            quoted_os = "\n".join([f"> {line}" for line in os_text.split("\n")])
            embed.add_field(name="💭 靈魂 OS 意識流", value=quoted_os, inline=False)
            
            # 3. 決定發言
            speech = persona_response.final_speech
            if speech:
                short_speech = speech[:250] + "..." if len(speech) > 250 else speech
                embed.add_field(name="🗣️ 決定發言", value=f"```\n{short_speech}\n```", inline=False)
            else:
                embed.add_field(name="🤐 決定發言", value="**拒絕發言 (保持沉默)**", inline=False)
                
            await channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ 情感遙測發送錯誤: {e}")


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

        # 為了 telemetry 輸出，先將 new_message 轉成簡潔便於閱讀的字串
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

        # 初始化本次的工具紀錄與暫存狀態
        self._last_executed_tools = []
        self._last_search_results = []
        self._current_location_info = location_info

        response_text = ""
        interaction_id = None

        try:
            # 增加全域配額生理記帳
            if not self._increment_usage():
                print("⚠️ [Global Ledger] 今日發言額度已達上限，暫停生成。")
                return "😵 (今天累了，我的生理能量已經用完囉，明天見！)", None

            # 呼叫 ADK 官方非同步生成器執行推理與 Tools 循環
            async for event in self.runner.run_async(
                user_id=user_id,
                session_id=session_id,
                new_message=msg_content
            ):
                # 1. 實時捕捉大腦內心 thought OS 簽章
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if getattr(part, 'thought_signature', None) and part.text:
                            # 發現 thought OS，發送情感遙測 (Discord 灰引言渲染)
                            # 包裹成 PersonaResponse 與舊 telemetry 相容
                            from pydantic import BaseModel
                            class FakePersonaResponse(BaseModel):
                                situation_analysis: str = "環境與情緒自然流轉"
                                internal_thought: str = part.text
                                final_speech: str = ""
                            asyncio.create_task(self._emit_chat_telemetry(FakePersonaResponse(internal_thought=part.text), telemetry_msg, location_info))

                # 2. 實時捕捉即時工具調用
                if event.actions and event.actions.function_calls:
                    for fc in event.actions.function_calls:
                        # 金色 Embed 背景播報
                        fc_args = fc.arguments if hasattr(fc, 'arguments') else {}
                        asyncio.create_task(self._emit_telemetry_live(f"🔧 **工具呼叫**: `{fc.name}`\n  * 參數: `{fc_args}`"))

                # 3. 實時捕捉大腦回覆與對話 ID
                if event.id:
                    interaction_id = event.id
                if event.content and event.content.parts:
                    for part in event.content.parts:
                        if part.text:
                            response_text += part.text

            # 決策完成後發射邏輯分析字卡 (與舊 telemetry 緊密相容)
            from pydantic import BaseModel
            class FakeMemoryState(BaseModel):
                needs_reply: bool = True
                current_goal: str = "與親愛的使用者進行貼心交流"
                suggested_sleep_seconds: int = self.next_sleep_duration
                sleep_intent: Optional[str] = self.sleep_intent
            asyncio.create_task(self._emit_logic_telemetry(FakeMemoryState(), telemetry_msg, location_info))

        except Exception as e:
            print(f"❌ [ADK Runner] 執行出錯: {e}")
            return f"😵 (大腦思考時發生未預期錯誤: {e})", None

        return response_text, interaction_id
    # --- Main Helper Methods ---

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

    
    def _increment_usage(self):
        quota_date_str = datetime.now(ZoneInfo("America/Los_Angeles")).strftime('%Y-%m-%d')
        if self.daily_usage.get("date") != quota_date_str:
            self.daily_usage = {"date": quota_date_str, "requests": 0, "tokens": 0}
        if self.daily_usage["requests"] >= (self.daily_limit_requests * 0.9):
            print(f"⚠️ [Global Ledger] 警告：今日額度已達 90% ({self.daily_usage['requests']}/{self.daily_limit_requests})")
            return False
        self.daily_usage["requests"] += 1
        self._save_json(self.usage_file, self.daily_usage)
        print(f"📊 [Global Ledger] 今日累積呼叫: {self.daily_usage['requests']} 次 / {self.daily_limit_requests} 次上限")
        return True

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
  - 今天已消耗次數：{self.daily_usage.get('requests', 0)} 次。
  - 額度重置規則：夏令時間（約 3 月中至 11 月初）為台灣時間每天下午 3 點 (15:00) 重置；冬令時間為下午 4 點 (16:00) 重置。
  - **生存抉擇**：妳沒有額外的疲勞值設定，妳的 500 次配額就是妳唯一的體力。妳必須透過設定 `suggested_sleep_seconds` 來強制自己休眠，以確保能存活到下午 3 點重置。一切由妳自行決定。
- 📍 所在空間座標：{location_context}
- 👁️ 視覺可解析之符號：
{emoji_docs}

# ==========================================
# 【記憶與環境 (The Environment)】
# ==========================================
{knowledge_context if knowledge_context else ""}
{facts_context if facts_context else ""}

妳只能透過 Pydantic 表單與這個宇宙互動。如果覺得過度疲勞，妳有權利選擇休眠 (final_speech: null)。請根據上述物理感官與記憶，決定妳的下一個動作。
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
                print(f"🌍 [Debug] Location Info:\n{location_info}")
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
            
            # Build History (Stateless)
            api_messages = []
            if self.memory_manager:
                try:
                    raw_history = await self.memory_manager.get_recent_chat_history(limit=20)
                    for msg in raw_history:
                        role = msg.get("role", "user")
                        content = msg.get("content", "")
                        if "parts" in msg:
                            api_messages.append(msg)
                        else:
                            api_messages.append({"role": role, "parts": [{"text": content}]})
                    
                    # Gemini API 要求第一條歷史必須是 user 角色
                    while api_messages and api_messages[0].get("role") != "user":
                        api_messages.pop(0)
                except Exception as e:
                    print(f"⚠️ [Memory] DB 載入短期歷史失敗: {e}")

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
                                # Image Hashing Logic
                                try:
                                    img_hash = hashlib.sha256(image_data).hexdigest()
                                    if self.memory_manager:
                                        existing = await self.memory_manager.check_image_hash(img_hash)
                                        if existing:
                                            ts = existing['created_at'].strftime('%Y-%m-%d %H:%M')
                                            # TextContentParam 格式
                                            current_user_parts.append({"type": "text", "text": f"\n[系統提示: 這張圖片在 {ts} 由 {existing['user_id']} 傳送過。]"})
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
                
                # 偵測並抓取 URL 網頁內容 (Extract URL Content)
                url_hints = []
                found_urls = re.findall(r'https?://[^\s]+', text_content)
                for url in found_urls:
                    print(f"🔗 [Link Fetcher] 偵測到網址: {url}，正在解析網頁內容...")
                    fetched_val = await self.fetch_url_content(url)
                    if fetched_val:
                        url_hints.append(f"\n[系統提示 - 連結解析: {url}]\n{fetched_val}")
                
                if url_hints:
                    text_content += "\n" + "\n".join(url_hints)

                if sticker_info: text_content += f" {sticker_info}"
                if not text_content and not msg.attachments and not msg.stickers: text_content = "(無內容)"
                
                # Format: [Andy | 朋友 | 12:00] (回覆 Bob: "...") Content
                user_header = f"[{msg.author.display_name} ({msg.author.name}) | 朋友 | {datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M')}]\n"
                
                # Combine parts — 使用 TextContentParam 格式
                final_text = user_header + reply_context + text_content + "\n"
                current_user_parts.append({"type": "text", "text": final_text})

            # 使用 parts 格式 — 會在 _convert_history 中統一轉換為 TurnParam
            api_messages.append({"role": "user", "parts": current_user_parts})

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
                    final_response = response_text
                    for k, v in self.emojis.items():
                        final_response = final_response.replace(f"[{k}]", v)

                    await channel.send(final_response)

                    # Log AI Response
                    if self.memory_manager:
                        await self.memory_manager.log_chat(role="model", content=response_text, session_id=f"discord_{channel.id}", interaction_id=interaction_id)

                    # Update History (Stateless - 已交由 log_chat 處理，無需操作 RAM)
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
                                    final_response = response_text
                                    for k, v in self.emojis.items():
                                        final_response = final_response.replace(f"[{k}]", v)
                                    
                                    await channel.send(final_response)
                                    
                                    if self.memory_manager:
                                        await self.memory_manager.log_chat(role="model", content=response_text, session_id=f"discord_{channel.id}", interaction_id=interaction_id)
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
