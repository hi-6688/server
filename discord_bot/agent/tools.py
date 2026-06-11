# -*- coding: utf-8 -*-
from typing import Any, List, Dict
import time
from google.genai import types
from google.adk.tools import AgentTool, ToolContext
from google.adk.tools.agent_tool import _get_input_schema, _get_output_schema, _part_to_text
from google.adk.utils.context_utils import Aclosing
from google.adk.runners import Runner
from google.adk.sessions.in_memory_session_service import InMemorySessionService
from google.adk.memory.in_memory_memory_service import InMemoryMemoryService
from google.adk.tools._forwarding_artifact_service import ForwardingArtifactService
from google.adk.utils._schema_utils import validate_schema

class HiHiAgentTool(AgentTool):
    """
    自訂的 HiHi 智能體委派工具 (HiHiAgentTool)，繼承自官方的 AgentTool。
    用於在子代理執行時，精確發射實時遙測（Live Telemetry）並記錄執行耗時與 Trace。
    """
    def __init__(
        self,
        agent,
        telemetry_mirror,
        orchestrator, # 指向 AgentOrchestrator 實體物件
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
        self.orchestrator = orchestrator # 大腦編排器實體
        
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
            
        if session_id not in self.orchestrator._session_traces:
            self.orchestrator._session_traces[session_id] = []
        trace_list = self.orchestrator._session_traces[session_id]

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


def get_agent_tools(orchestrator) -> list:
    """
    獲取主大腦綁定的自訂 AI 工具清單。
    """
    async def manage_fact_tool(action: str, user_id: str, content: str, category: str = "Data") -> str:
        """管理關於使用者的長期事實 (CRUD)。當你發現新的事實，或發現舊事實有誤時使用。
        
        Args:
            action: 'add' (新增) 或 'delete' (刪除/修正)
            user_id: 對象名字 (例如 'Andy')
            content: 事實內容 (例如: '喜歡吃拉麵')
            category: 類別，可填 'Data' (客觀資料: 生日/職業) 或 'Impression' (主觀印象: 個性/愛好)
        """
        return await orchestrator.manage_fact(action, user_id, content, category)

    async def learn_knowledge_tool(term: str, definition: str, category: str = "General") -> str:
        """當使用者教你新詞彙、梗、或伺服器設定時使用。這會存入你的[知識庫] (RAG)。
        
        Args:
            term: 關鍵詞 (例如: 'Hammer', '炸服')
            definition: 定義與解釋
            category: 類別，可填 'Emoji', 'Slang', 'Lore', 'Person', 'General'
        """
        return await orchestrator.learn_knowledge(term, definition, category)

    async def schedule_next_sleep_tool(seconds: Any, intent: Any) -> str:
        """當妳想決定自己接下來要主動休眠多久（秒）並設定醒來後的鬧鐘備忘錄時呼叫此工具。
        這是妳用來保護「生命配額」的唯一手段。若配額充足且群組熱鬧，建議設定 3600；若配額快耗盡，請設定 14400 或更長。
        
        Args:
            seconds: 睡眠秒數
            intent: 醒來後要主動做的事情備忘錄 (例如：『等待60秒後回答問題』)
        """
        try:
            from agent.schemas import SleepScheduleParams
            from utils.scheduler_tools import execute_sleep_scheduling
            validated = SleepScheduleParams(seconds=seconds, intent=intent)
            return await execute_sleep_scheduling(orchestrator.cog_instance, validated.seconds, validated.intent)
        except Exception as e:
            print(f"⚠️ [schedule_next_sleep_tool] 參數校正失敗: {e}，將採用安全預設值 (3600秒)")
            from utils.scheduler_tools import execute_sleep_scheduling
            return await execute_sleep_scheduling(orchestrator.cog_instance, 3600, None)

    return [
        manage_fact_tool,
        learn_knowledge_tool,
        schedule_next_sleep_tool
    ]
