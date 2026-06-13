# -*- coding: utf-8 -*-
import discord
import os
import asyncio
from datetime import datetime, timezone, timedelta
from pydantic import BaseModel, Field
from google.genai import types

class TranslationResult(BaseModel):
    translated_text: str = Field(
        description="翻譯成繁體中文（台灣）後的內容。請僅包含翻譯後的內容本身。"
    )

class TelemetryMirror:
    def __init__(self, bot, inner_world_channel_id: int, client=None):
        self.bot = bot
        self.inner_world_channel_id = inner_world_channel_id
        self.client = client # 儲存 AI Client 實體 (client: google-genai 客戶端物件)

    async def _translate_thought_with_gemma(self, thought_text: str) -> str:
        # 使用 Gemma 4 翻譯思考鏈 (_translate_thought_with_gemma: 翻譯大腦英文思考過程的非同步函數)
        # 💡 使用 models/gemma-4-26b-a4b-it 進行高質量的雙語翻譯對齊
        if not self.client or not thought_text or thought_text == "N/A":
            return thought_text
            
        try:
            # 建立翻譯專屬的提示詞 (prompt: Gemma 翻譯專用引導詞)
            prompt = f"請將以下 AI 的英文思考過程翻譯為流暢、自然的繁體中文（台灣）。\n\n英文思考內容：\n{thought_text}"
            
            # 使用非同步 Client 呼叫 Gemma 4 26B (response: 翻譯模型生成之結果)
            response = await self.client.aio.models.generate_content(
                model="models/gemma-4-26b-a4b-it",
                contents=prompt,
                config=types.GenerateContentConfig(
                    response_mime_type="application/json",
                    response_schema=TranslationResult
                )
            )
            if response and response.text:
                import json
                result_data = json.loads(response.text.strip())
                return result_data.get("translated_text", "").strip()
        except Exception as e:
            print(f"⚠️ [Gemma 4 翻譯] 失敗: {e}，將回退展示原始英文思緒。")
        return thought_text

    async def _get_channel(self):
        if not self.inner_world_channel_id:
            return None
        channel = self.bot.get_channel(self.inner_world_channel_id)
        if not channel:
            try:
                channel = await self.bot.fetch_channel(self.inner_world_channel_id)
            except Exception as e:
                print(f"⚠️ 遙測失敗：找不到頻道 ({self.inner_world_channel_id}): {e}")
                return None
        return channel

    async def emit_logic_telemetry(
        self,
        memory_state,
        trigger_text,
        location_info,
        daily_usage,
        daily_limit,
        trace_events=None,
        facts_text="N/A",
        short_history=None,
        translated_thought="N/A",
        final_speech="🤐 保持沉默 (未發言)",
        usage_metadata=None,
        interaction_id=None,
        user_profile="N/A" # 💡 新增用戶人設印象 Profile 參數
    ):
        """
        發射事後綜合報告卡 (Post-Mortem Embed)。
        將空間座標、觸發訊息、配額與休眠、記憶載入庫 (短期/長期/核心DNA)、執行軌跡 (Trace) 以及大腦內部呢喃 (OS)
        以視覺化層級整合在一張精美的卡片中發送。
        """
        channel = await self._get_channel()
        if not channel:
            return
        
        try:
            # 建立大腦呢喃內容區塊，放在 Description 享受 4000 字元超大空間 (quoted_os: 內心 OS)
            os_thought = "N/A"
            if isinstance(translated_thought, asyncio.Task) or asyncio.iscoroutine(translated_thought):
                try:
                    os_thought = await translated_thought
                except Exception as ex_trans:
                    print(f"⚠️ [Telemetry] 獲取翻譯思緒失敗: {ex_trans}")
                    os_thought = "N/A"
            else:
                os_thought = translated_thought if translated_thought else "N/A"

            if os_thought == "N/A" or not os_thought.strip():
                os_thought = "💡 官方新版 API (Interactions v2.0) 已將思考過程限制為安全驗證簽名 (Signature)，目前未對外開放明文讀取。"
            
            quoted_os = "\n".join([f"> {line}" for line in os_thought.split("\n")])
            if len(quoted_os) > 3500:
                quoted_os = quoted_os[:3450] + "\n> ... (已達 Discord 內文長度限制)"
                
            embed_desc = f"**📝 大腦內部原始呢喃 (Translated Thought)**:\n{quoted_os}"
            
            # 使用高雅藍色作為綜合報告的主色 (embed: 綜合報告卡片)
            embed = discord.Embed(
                title="🧠 思考與狀態分析 (綜合報告)", 
                color=0x3a86ff, 
                description=embed_desc,
                timestamp=datetime.now(timezone(timedelta(hours=8)))
            )
            
            # 1. 空間座標與觸發源 (並排 inline=True)
            short_trigger = trigger_text[:100] + "..." if len(trigger_text) > 100 else trigger_text
            embed.add_field(name="📍 空間座標", value=f"```\n{location_info.strip()}\n```" if location_info else "```位置未知```", inline=True)
            embed.add_field(name="🎯 觸發訊息", value=f"```\n{short_trigger}\n```", inline=True)
            
            # 2. 生存指標與生理調控
            req = daily_usage.get('requests', 0)
            limit = daily_limit
            pct = (req / limit) * 100 if limit > 0 else 0
            color_emoji = "🟢"
            if pct > 60: color_emoji = "🟡"
            if pct > 90: color_emoji = "🔴"
            
            # 讀取核心記憶字數 (core_dna_status: 核心記憶載入狀態與字數)
            core_dna_status = "🧬 核心 DNA: 🔴 未載入"
            try:
                core_path = "/home/hi6688/servers/discord_bot/data/hihi/core_memory.md"
                if os.path.exists(core_path):
                    with open(core_path, "r", encoding="utf-8") as f:
                        dna_len = len(f.read())
                    core_dna_status = f"🧬 核心 DNA: 🟢 已載入 ({dna_len} 字)"
            except Exception as ex_dna:
                print(f"⚠️ [Telemetry DNA] 讀取核心記憶失敗: {ex_dna}")
            
            vitals = f"{color_emoji} 消耗配額: **{req} / {limit}** ({pct:.1f}%)\n"
            vitals += f"💤 自主休眠決策: **{memory_state.suggested_sleep_seconds} 秒**\n"
            vitals += f"{core_dna_status}"
            if memory_state.sleep_intent:
                vitals += f"\n⏰ 鬧鐘備忘錄: `{memory_state.sleep_intent}`"
            embed.add_field(name="⚡ 配額、休眠與 DNA 狀態", value=vitals, inline=False)
            
            # 3. 📥 [Context] 記憶載入庫 (短期對話記憶 + 長期事實)
            history_str = "N/A"
            if short_history:
                formatted_history = [f"> {idx+1}. {line[:120]}" for idx, line in enumerate(short_history)]
                history_str = "\n".join(formatted_history)
                
            facts_str = "N/A"
            if facts_text and facts_text != "N/A":
                facts_str = "\n".join([f"> {line}" for line in facts_text.split("\n") if line.strip()])
                
            user_profile_str = "N/A"
            if user_profile and user_profile != "N/A":
                user_profile_str = "\n".join([f"> {line}" for line in user_profile.split("\n") if line.strip()])

            context_val = f"**滾動壓縮對話摘要**:\n{history_str}\n\n**長期人設印象 (Profile)**:\n{user_profile_str}\n\n**長期事實偏好**:\n{facts_str}"
            if len(context_val) > 1024:
                context_val = context_val[:1000] + "\n... (記憶載入庫超長截斷)"
            embed.add_field(name="📥 [Context] 記憶載入庫", value=context_val, inline=False)
            
            # 4. 🚀 執行軌跡 (Trace)
            trace_str = "N/A"
            if trace_events:
                formatted_trace = []
                for idx, t in enumerate(trace_events):
                    # 判斷是否為子代理相關，加上全形空格縮排
                    indent_prefix = "　　" if "子代理" in t or "GoogleSearch" in t or "FileSearch" in t or "獲得檢索結果" in t or ("任務完成" in t and not "search_specialist 任務完成" in t) else ""
                    formatted_trace.append(f"> {indent_prefix}{idx+1}. {t}")
                trace_str = "\n".join(formatted_trace)
            if len(trace_str) > 1024:
                trace_str = trace_str[:1000] + "\n... (軌跡超長截斷)"
            embed.add_field(name="🚀 執行軌跡 (Trace)", value=trace_str, inline=False)
            
            # 5. 決定回覆內容 (精簡呈現，限制 250 字)
            short_speech = final_speech[:250] + "..." if len(final_speech) > 250 else final_speech
            embed.add_field(
                name="🗣️ 決定回覆內容", 
                value=f"```\n{short_speech}\n```" if short_speech and short_speech.strip() else "```🤐 拒絕發言 (保持沉默)```", 
                inline=False
            )
            
            # 6. 展示 Token 消耗與 Interaction ID
            if usage_metadata:
                prompt_tokens = usage_metadata.prompt_token_count
                completion_tokens = usage_metadata.candidates_token_count
                total_tokens = usage_metadata.total_token_count
                token_details = f"🎯 輸入: **{prompt_tokens}** | ✍️ 輸出: **{completion_tokens}** | ⚡ 總計: **{total_tokens}**"
                embed.add_field(name="📊 官方實時 Token 消耗", value=token_details, inline=False)
                
            if interaction_id:
                embed.set_footer(text=f"Interaction ID: {interaction_id}")
                
            await channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ 綜合邏測發送錯誤: {e}")

    async def emit_telemetry_live(self, content):
        """實時遙測，用於播報工具執行等單行訊息。"""
        channel = await self._get_channel()
        if not channel:
            return
        try:
            # 移除時間戳記以達到極致的簡明與緊湊性
            embed = discord.Embed(description=content, color=0xffd166)
            await channel.send(embed=embed)
        except Exception as e:
            print(f"⚠️ 實時遙測發送錯誤: {e}")

    async def emit_chat_telemetry(self, persona_response, trigger_text, location_info="", usage_metadata=None, interaction_id=None):
        """相容保留，以防其他地方仍有呼叫"""
        pass
