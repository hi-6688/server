
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
from google.adk.tools import AgentTool, url_context, ToolContext # 導入多智能體委派工具、官方內建 url_context 讀網頁工具與 ToolContext
from google.adk.telemetry.setup import maybe_set_otel_providers # 導入官方遙測設定
from google.adk.apps.app import App, EventsCompactionConfig # 導入官方 ADK App 容器與事件壓縮配置
# 💡 額外導入 ADK 內部模組以供自訂 HiHiAgentTool 繼承覆寫使用
from google.adk.tools.agent_tool import _get_input_schema, _get_output_schema, _part_to_text
from google.adk.utils.context_utils import Aclosing
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService

# 💡 導入 APScheduler 4.0 官方異步排程核心與持久化組件
from apscheduler import AsyncScheduler
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import create_async_engine

from google.adk.tools._forwarding_artifact_service import ForwardingArtifactService
from google.adk.utils._schema_utils import validate_schema
from typing import Any


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

class HiHiAgentTool(AgentTool):
    """
    自訂的 HiHi 智能體委派工具 (HiHiAgentTool)，繼承自官方的 AgentTool。
    用於在子代理執行時，精確發射實時遙測（Live Telemetry）並記錄執行耗時與 Trace。
    """
    def __init__(
        self,
        agent,
        telemetry_mirror,
        parent_cog, # 指向 AIChat 實體物件
        skip_summarization: bool = False,
        *,
        include_plugins: bool = True,
        propagate_grounding_metadata: bool = False
    ):
        super().__init__(
            agent,
            skip_summarization,
            include_plugins=include_plugins,
            propagate_grounding_metadata=propagate_grounding_metadata
        )
        self.telemetry_mirror = telemetry_mirror # 遙測鏡像物件
        self.parent_cog = parent_cog # 父層 Cog 實體
        
    async def run_async(
        self,
        *,
        args: dict[str, Any],
        tool_context: ToolContext
    ) -> Any:
        # 動態獲取 session_id 並對齊 Trace 列表 (session_id: 當前會話識別碼, trace_list: 當前會話追蹤列表)
        session_id = "default"
        if tool_context._invocation_context and tool_context._invocation_context.session_id:
            session_id = tool_context._invocation_context.session_id
            
        if session_id not in self.parent_cog._session_traces:
            self.parent_cog._session_traces[session_id] = []
        trace_list = self.parent_cog._session_traces[session_id]

        # 取得請求參數文字 (request_text: 取得子代理的輸入文字)
        request_text = args.get('request', '(無指令)')
        # 縮減長度避免 Embed 卡片超長 (short_request: 縮短的請求文字)
        short_request = request_text[:120] + "..." if len(request_text) > 120 else request_text
        
        # 實時發射子代理啟動的遙測播報 (emit_telemetry_live: 發射實時遙測)
        await self.telemetry_mirror.emit_telemetry_live(
            f"　　🔎 **[子代理 {self.name}] 啟動**！接收指令：\n　　> {short_request}"
        )
        
        # 記錄啟動 Trace 與時間戳記 (start_time: 子代理執行開始時間)
        start_time = time.time()
        trace_list.append(f"{self.name} 啟動：接收指令 \"{short_request}\"")

        # 以下複寫官方 AgentTool.run_async 的執行流程
        if self.skip_summarization:
            tool_context.actions.skip_summarization = True

        input_schema = _get_input_schema(self.agent)
        if input_schema:
            input_value = input_schema.model_validate(args)
            content = types.Content(
                role='user',
                parts=[
                    types.Part.from_text(
                        text=input_value.model_dump_json(exclude_none=True)
                    )
                ],
            )
        else:
            content = types.Content(
                role='user',
                parts=[types.Part.from_text(text=args['request'])],
            )
            
        invocation_context = tool_context._invocation_context
        parent_app_name = (
            invocation_context.app_name if invocation_context else None
        )
        child_app_name = parent_app_name or self.agent.name
        plugins = (
            tool_context._invocation_context.plugin_manager.plugins
            if self.include_plugins
            else None
        )
        
        runner = Runner(
            app_name=child_app_name,
            agent=self.agent,
            artifact_service=ForwardingArtifactService(tool_context),
            session_service=InMemorySessionService(),
            memory_service=InMemoryMemoryService(),
            credential_service=tool_context._invocation_context.credential_service,
            plugins=plugins,
        )
        
        if self.include_plugins:
            runner.plugin_manager.set_skip_closing_plugins(True)

        state_dict = {
            k: v
            for k, v in tool_context.state.to_dict().items()
            if not k.startswith('_adk')
        }
        
        session = await runner.session_service.create_session(
            app_name=child_app_name,
            user_id=tool_context._invocation_context.user_id,
            state=state_dict,
        )

        last_content = None
        last_grounding_metadata = None
        has_sent_rag_receipt = False # 是否已發射 RAG 接收遙測

        async with Aclosing(
            runner.run_async(
                user_id=session.user_id, session_id=session.id, new_message=content
            )
        ) as agen:
            async for event in agen:
                # 轉送 state_delta
                if event.actions.state_delta:
                    tool_context.state.update(event.actions.state_delta)
                
                # 實時監聽子代理內部的工具呼叫 (func_calls: 偵測子代理工具呼叫)
                func_calls = event.get_function_calls()
                if func_calls:
                    for fc in func_calls:
                        fc_args = fc.args if hasattr(fc, 'args') else {}
                        # 實時播報：子代理調用工具 (fc_desc: 格式化後的工具呼叫資訊)
                        fc_desc = f"　　🔧 **[子代理 行動]** 呼叫了工具：`{fc.name}`\n　　  * 參數: `{fc_args}`"
                        await self.telemetry_mirror.emit_telemetry_live(fc_desc)
                        # 寫入 Trace 軌跡
                        trace_list.append(f"{self.name} -> 呼叫 -> {fc.name}")
                
                # 捕捉子代理取得的 RAG (File Search) 回應內容
                if event.content:
                    last_content = event.content
                    last_grounding_metadata = event.grounding_metadata
                    
                    # 當子代裡收到 RAG 檢索資料（即開始有內容輸出且尚未播報接收時）
                    if not has_sent_rag_receipt:
                        parts_text = []
                        if event.content.parts:
                            for p in event.content.parts:
                                if p.text and not getattr(p, 'thought', False):
                                    parts_text.append(p.text)
                        
                        text_summary = " ".join(parts_text).strip()
                        if text_summary:
                            # 節錄前 100 字元 (snippet: 擷取的精華文本)
                            snippet = text_summary[:100] + "..." if len(text_summary) > 100 else text_summary
                            # 實時播報：子代理接收檢索結果
                            await self.telemetry_mirror.emit_telemetry_live(
                                f"　　📥 **[子代理 接收]** 獲得檢索結果，正在彙整客觀報告...\n　　  * 節錄: *\"{snippet}\"*"
                            )
                            has_sent_rag_receipt = True
                            trace_list.append(f"{self.name} -> 獲得檢索結果：\"{snippet}\"")

        await runner.close()

        if last_content is None or last_content.parts is None:
            tool_result = ''
        else:
            parts_text_gen = (_part_to_text(p) for p in last_content.parts if not p.thought)
            merged_text = '\n'.join(t for t in parts_text_gen if t)
            output_schema = _get_output_schema(self.agent)
            if output_schema:
                tool_result = validate_schema(output_schema, merged_text)
            else:
                tool_result = merged_text

        if self.propagate_grounding_metadata and last_grounding_metadata:
            tool_context.state['temp:_adk_grounding_metadata'] = (
                last_grounding_metadata
            )

        # 計算耗時並紀錄 Trace (duration: 子代理總花費秒數)
        duration = time.time() - start_time
        trace_list.append(f"{self.name} 任務完成 (等待 {duration:.1f}秒)")
        
        return tool_result


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

        # 💓 異步排程器 (APScheduler 4.0 Engine)
        self.scheduler = None
        self.scheduler_task = None
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
        self._session_traces = {} # 存放各會話執行軌跡的字典 (self._session_traces: 執行軌跡快取)
        
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
                        HiHiAgentTool(agent=self.search_agent, telemetry_mirror=self.telemetry_mirror, parent_cog=self)  # 🧠 注入自訂搜尋專家委派工具 (HiHiAgentTool: 帶有遙測的代理工具)
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
        # 取消排程器背景任務，以觸發 context manager 結束釋放資源
        if self.scheduler_task:
            self.scheduler_task.cancel()
        pass

    async def run_scheduler(self):
        """
        以背景協程方式執行 APScheduler v4.0 的 context manager，確保其生命週期與 Cog 對齊。
        """
        try:
            db_url = os.getenv("DATABASE_URL")
            cleaned_db_url = db_url.replace("postgres://", "postgresql+asyncpg://").replace("?sslmode=require", "")
            print(f"🔌 [APScheduler] 正在初始化 SQLAlchemyDataStore 連接: {cleaned_db_url.split('@')[-1]}")
            
            engine = create_async_engine(cleaned_db_url)
            data_store = SQLAlchemyDataStore(engine)
            
            async with AsyncScheduler(data_store) as scheduler:
                self.scheduler = scheduler
                print("💓 [APScheduler] 異步排程引擎啟動成功，並已在背景持續執行！")
                await scheduler.run_until_stopped()
        except asyncio.CancelledError:
            print("🧹 [APScheduler] 背景排程任務被取消，已安全退出。")
        except Exception as e:
            print(f"❌ [APScheduler] 排程器運行出錯: {e}")

    async def _init_ai(self):
        # 0. 啟動官方 OpenTelemetry 遙測追蹤
        try:
            maybe_set_otel_providers()
            print("📊 [Telemetry] 官方 OpenTelemetry 遙測系統啟動成功！")
        except Exception as e:
            print(f"⚠️ [Telemetry] 遙測系統啟動失敗: {e}")

        # 1. 啟動 APScheduler 4.0 異步排程系統 (帶有 PostgreSQL 持久化)
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            print("🔌 [APScheduler] 正在背景啟動排程任務...")
            self.scheduler_task = self.bot.loop.create_task(self.run_scheduler())
        else:
            print("⚠️ [APScheduler] 未配置 DATABASE_URL，無法啟用持久化排程器。")

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
                    
                    # 建立 File Search 原生 RAG 物件 (Google Search 已關閉)
                    fs_tool = types.Tool(
                        file_search=types.FileSearch(
                            file_search_store_names=[self.file_search_store_name]
                        )
                    )
                    # gs_tool = types.Tool(
                    #     google_search=types.GoogleSearch() # 🌐 因免費額度限制暫時關閉官方 Google 搜尋聯網功能
                    # )
                    
                    self.search_agent.generate_content_config.tools = [
                        fs_tool
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

        # 初始化與記錄本次會話執行軌跡 (self._session_traces: 各會話執行軌跡快取)
        self._session_traces[session_id] = []
        trace_list = self._session_traces[session_id]

        # 實時發射使用者傳送訊息的遙測播報 (emit_telemetry_live: 發送單行遙測)
        short_input = telemetry_msg[:120] + "..." if len(telemetry_msg) > 120 else telemetry_msg
        await self.telemetry_mirror.emit_telemetry_live(f"💬 **[User]** 傳送了訊息：\"{short_input}\"")
        await self.telemetry_mirror.emit_telemetry_live(f"🧠 **[主大腦 思考中]** 評估任務...")
        trace_list.append("主大腦評估任務中...")

        # 實時動態檢索長期 facts 並融入 System Instruction (ADK MemoryService 原生自動預載)
        facts_text = "N/A"
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
                    # 寫入 Trace 軌跡
                    trace_list.append("大腦載入長期記憶 Facts")
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
                        fc_args = fc.args if hasattr(fc, 'args') else {}
                        # 判斷是否為子代理任務委派
                        if fc.name == "search_specialist":
                            # 實時播報：任務委派
                            await self.telemetry_mirror.emit_telemetry_live(
                                "🤝 **[任務委派]** 主大腦呼叫了工具：`AgentTool(search_specialist)`。將控制權轉交子代理。"
                            )
                            trace_list.append("HiHiv3Agent -> 呼叫 -> search_specialist")
                            self._last_executed_tools.append("search_specialist")
                        else:
                            # 實時播報：主大腦調用工具
                            await self.telemetry_mirror.emit_telemetry_live(
                                f"🔧 **[主大腦 行動]** 呼叫了工具：`{fc.name}`\n  * 參數: `{fc_args}`"
                            )
                            trace_list.append(f"HiHiv3Agent -> 呼叫 -> {fc.name}")
                            self._last_executed_tools.append(fc.name)

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

            # 實時播報：若曾呼叫搜尋子代理，主大腦收到報告準備潤飾
            if "search_specialist" in self._last_executed_tools:
                await self.telemetry_mirror.emit_telemetry_live(
                    "🧠 **[主大腦 思考中]** 收到報告，準備進行最終擬人化潤飾..."
                )
                trace_list.append("主大腦獲得報告並彙整潤飾")
            else:
                trace_list.append("主大腦完成思考與回覆生成")

            # 對話結束後，重新獲取 session 以還原短期歷史對話 (short_history: 最近5句對話內容)
            short_history = []
            try:
                session_obj = await self.session_service.get_session(
                    app_name="HiHiDiscordBot",
                    user_id=user_id,
                    session_id=session_id
                )
                if session_obj and session_obj.events:
                    for ev in session_obj.events:
                        if ev.content and ev.content.parts:
                            text_parts = [p.text for p in ev.content.parts if p.text and not getattr(p, 'thought', False)]
                            if text_parts:
                                merged_text = " ".join(text_parts).strip()
                                if merged_text:
                                    role_name = "User" if ev.author == "user" else ev.author
                                    short_history.append(f"{role_name}: {merged_text}")
                    # 只擷取最後 5 句
                    short_history = short_history[-5:]
            except Exception as ex_hist:
                print(f"⚠️ [Short History] 還原短期記憶錯誤: {ex_hist}")

            # 決策完成後發射事後綜合報告卡 (已整合 emit_chat_telemetry 與舊 emit_logic_telemetry)
            from pydantic import BaseModel
            class FakeMemoryState(BaseModel):
                needs_reply: bool = True
                current_goal: str = "與親愛的使用者進行貼心交流"
                suggested_sleep_seconds: int = self.next_sleep_duration
                sleep_intent: Optional[str] = self.sleep_intent
                
            # 異步發射整合後的 Post-Mortem 大 Embed 卡片
            asyncio.create_task(self.telemetry_mirror.emit_logic_telemetry(
                memory_state=FakeMemoryState(),
                trigger_text=telemetry_msg,
                location_info=location_info,
                daily_usage=self.quota_manager.daily_usage,
                daily_limit=self.daily_limit_requests,
                trace_events=trace_list,
                facts_text=facts_text,
                short_history=short_history,
                translated_thought=translated_thought,
                final_speech=response_text,
                usage_metadata=latest_usage_metadata,
                interaction_id=interaction_id
            ))

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
        
        # 透過排程器更新下一次心跳排程，將鬧鐘重設至 1 小時之後
        await self.schedule_next_sleep(seconds=3600, intent=None)

        
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

    async def schedule_next_sleep(self, seconds: int, intent: str = None):
        """
        使用 APScheduler v4.0 動態安排下一次心跳甦醒任務。
        """
        if not self.scheduler:
            print("⚠️ [APScheduler] 排程器未啟動，無法安排睡眠。")
            return
            
        wakeup_time = datetime.now() + timedelta(seconds=seconds)
        self.sleep_intent = intent
        
        # 4.0 中以 DateTrigger 定義執行時間點
        # conflict_policy="replace" 實現覆寫更新
        await self.scheduler.add_schedule(
            self.execute_scheduled_wake,
            DateTrigger(run_time=wakeup_time),
            id="hihi_heartbeat_schedule",
            args=[intent],
            conflict_policy="replace"
        )
        print(f"⏰ [APScheduler 4.0] 已安排下一次主動甦醒：{wakeup_time}。備忘錄: '{intent}'")

    async def execute_scheduled_wake(self, intent: str):
        """
        時間到後，APScheduler 自動非同步觸發此方法發起主動閒聊。
        """
        print(f"💓 [APScheduler 4.0] 鬧鐘時間到，主動甦醒中。備忘意圖: '{intent}'")
        target_channel_id = 1467980863990927623
        channel = self.bot.get_channel(target_channel_id)
        
        if not channel:
            print(f"⚠️ [APScheduler] 找不到目標頻道 {target_channel_id}，放棄主動閒聊。")
            return
            
        try:
            current_time = datetime.now(timezone(timedelta(hours=8))).strftime('%m月%d日 %H:%M')
            base_prompt = await self._get_system_prompt("", f"頻道：{channel.name}", "", "")
            
            awaken_hint = f"*(時間來到了 {current_time}。休眠結束，腦海中浮現了先前的備忘錄：「{intent}」)*" if intent else f"*(時間來到了 {current_time})*"
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
                    print("😴 [APScheduler] AI 決定繼續裝死不發言。")
        except Exception as e:
            print(f"❌ [APScheduler] 主動閒聊失敗: {e}")


async def setup(bot):
    await bot.add_cog(AIChat(bot))
