# -*- coding: utf-8 -*-
from typing import Optional, Any
import discord
import os
import time
import asyncio
import aiohttp
import base64
from datetime import datetime, timezone, timedelta
from discord.ext import commands

# 💡 導入大一統 Agent 模組化元件
from agent import AgentOrchestrator, HeartbeatScheduler
from utils.quota_manager import QuotaManager
from utils.emoji_service import EmojiService

# --- 設定檔路徑 ---
BASE_DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'data')
DATA_DIR = os.path.join(BASE_DATA_DIR, 'hihi') # 嗨嗨專屬資料夾
EMOJI_FILE = os.path.join(DATA_DIR, 'emojis.json')
CORE_MEMORY_FILE = os.path.join(DATA_DIR, 'core_memory.md')

os.makedirs(DATA_DIR, exist_ok=True)

class AIChat(commands.Cog):
    """
    AIChat 控制器 (Cog)
    負責 Discord 訊息事件捕獲、緩衝去抖、位置與身份上下文準備，並委派大腦編排器與心跳排程器進行推理與調度。
    """
    def __init__(self, bot):
        self.bot = bot
        
        # 狀態 (Local Runtime State)
        self.is_override_active = False
        self.message_count = 0        
        self.response_task: Optional[asyncio.Task] = None
        self.message_buffer: list[discord.Message] = []
        self.sleep_intent = None
        self.next_sleep_duration = 3600
        self.last_message_time = time.time()

        # 載入設定檔與管理服務
        self.daily_limit_requests = 500
        self.usage_file = os.path.join(DATA_DIR, 'daily_usage.json')
        self.emoji_meanings_file = os.path.join(DATA_DIR, 'emoji_meanings.json')
        
        self.quota_manager = QuotaManager(usage_file=self.usage_file, daily_limit=self.daily_limit_requests)
        self.emoji_service = EmojiService(emoji_file=EMOJI_FILE, meanings_file=self.emoji_meanings_file)

        # 🧠 大腦編排器實例化
        self.orchestrator = AgentOrchestrator(bot=self.bot, cog_instance=self)
        # 💓 異步定時心跳排程器實例化
        self.scheduler = HeartbeatScheduler(bot=self.bot, cog_instance=self)

        # 啟動背景初始化任務
        self.bot.loop.create_task(self._init_ai())

    def cog_unload(self):
        # 停止背景定時排程器，確保物理釋放資源
        self.scheduler.stop()

    async def _init_ai(self):
        # 異步初始化大腦編排器 (雲端 File Search Store 與思考鏈設定)
        await self.orchestrator.initialize()
        # 啟動背景持久化心跳排程器
        await self.scheduler.start()
        print(f"✅ [AIChat] 模組化 AI 大腦與排程器初始化完成！(模型: {self.orchestrator.model_name})")

    async def schedule_next_sleep(self, seconds: int, intent: str = None):
        """相容性引導：導向排程器組件"""
        await self.scheduler.schedule_next_sleep(seconds, intent)

    @commands.Cog.listener()
    async def on_message(self, message):
        # 🔍 偵測收到的所有訊息以供排查
        print(f"📥 [on_message] 收到來自 {message.author.name} (Bot: {message.author.bot}) 在頻道 {message.channel.id} 的訊息: {message.content[:50]}")
        
        # 1. Guards
        CONCH_BOT_ID = 1381482872845635614
        if message.author.bot and message.author.id != CONCH_BOT_ID: return
        
        channel_ids_str = os.getenv("AI_CHANNEL_ID", "0").split('#')[0]
        active_channel_ids = []
        for cid in channel_ids_str.split(','):
            try:
                cid = cid.strip()
                if cid: active_channel_ids.append(int(cid))
            except ValueError: pass
            
        if not active_channel_ids:
            active_channel_ids = [0]
            
        if message.channel.id not in active_channel_ids and not self.is_override_active: return
        
        # 如果是神奇嗨螺的訊息，只加入 buffer 但不觸發回覆
        if message.author.bot and message.author.id == CONCH_BOT_ID:
            self.message_buffer.append(message)
            print(f"🐚 [Buffer] Conch bot message added (passive): {message.content[:30]}...")
            return
        
        print(f"📨 [Buffer] New message from {message.author.display_name}: {message.content[:20]}...")
        
        # 透過排程器更新下一次心跳排程，將鬧鐘重設至 1 小時之後
        await self.scheduler.schedule_next_sleep(seconds=3600, intent=None)

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
            
            if not self.message_buffer: return

            # Snapshot & Clear
            messages_to_process = list(self.message_buffer)
            self.message_buffer.clear()
            
            print(f"🧠 [Agent] Processing batch of {len(messages_to_process)} messages...")
            last_message = messages_to_process[-1]
            self.last_message_time = time.time()
            
            # Location Info
            try:
                guild_name = last_message.guild.name if last_message.guild else "私人訊息 (Private)"
                channel_name = channel.name if hasattr(channel, 'name') else "DM"
                location_info = f"- 伺服器 (Server): {guild_name}\n- 頻道 (Channel): {channel_name}"
            except: location_info = "- 位置未知"

            # Self Identity
            self_identity = ""
            try:
                if last_message.guild:
                    me = last_message.guild.me
                    roles = [r.name for r in me.roles if r.name != "@everyone"]
                    self_identity = f"- 我的暱稱 (My Nickname): {me.display_name}\n- 我的身份組 (My Roles): {', '.join(roles)}"
            except: pass

            # System Prompt
            system_prompt = await self.orchestrator.get_system_prompt("", location_info, "", self_identity)
            
            # Construct Current Turn (Merge Messages)
            current_user_parts = []
            
            for msg in messages_to_process:
                # Handle Context (Reply)
                reply_context = ""
                if msg.reference:
                    try:
                        ref_msg = msg.reference.resolved
                        if not ref_msg and msg.reference.channel_id == channel.id:
                            try:
                                ref_msg = await channel.fetch_message(msg.reference.message_id)
                            except: pass
                        
                        if ref_msg:
                            ref_content = ref_msg.content[:50] + "..." if len(ref_msg.content) > 50 else ref_msg.content
                            if not ref_content and ref_msg.attachments: ref_content = "[圖片]"
                            if not ref_content and ref_msg.stickers: ref_content = f"[貼圖: {ref_msg.stickers[0].name}]"
                            reply_context = f"(回覆 {ref_msg.author.display_name}: \"{ref_content}\") "
                    except: pass

                # Handle Images (Attachments)
                if msg.attachments:
                    for attachment in msg.attachments:
                        if attachment.content_type and attachment.content_type.startswith("image/"):
                            if attachment.size > 8 * 1024 * 1024: continue
                            try:
                                image_data = await attachment.read()
                                current_user_parts.append({
                                    "type": "image",
                                    "data": base64.b64encode(image_data).decode('utf-8'),
                                    "mime_type": attachment.content_type
                                })
                            except: pass

                # Handle Stickers (Vision + Text)
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
                                            current_user_parts.append({
                                                "type": "image",
                                                "data": base64.b64encode(data).decode('utf-8'),
                                                "mime_type": "image/png"
                                            })
                        except Exception as e:
                            print(f"⚠️ Sticker processing error: {e}")
                    
                    sticker_info = f"[傳送了貼圖: {', '.join(sticker_names)}]"

                # Assemble Text
                text_content = msg.content if msg.content else ""
                if sticker_info: text_content += f" {sticker_info}"
                if not text_content and not msg.attachments and not msg.stickers: text_content = "(無內容)"
                
                user_header = f"[{msg.author.display_name} ({msg.author.name}) | 朋友 | {datetime.now(timezone(timedelta(hours=8))).strftime('%H:%M')}]\n"
                final_text = user_header + reply_context + text_content + "\n"
                current_user_parts.append({"type": "text", "text": final_text})

            # Call Orchestrator
            async with channel.typing():
                response_text, interaction_id = await self.orchestrator.call_adk_runner(
                    user_id=str(last_message.author.id),
                    session_id=f"discord_{channel.id}",
                    new_message=current_user_parts,
                    system_instruction=system_prompt,
                    location_info=location_info
                )

                if response_text and response_text.strip() and not response_text.startswith("😵"):
                    final_response = self.emoji_service.replace_emojis(response_text)
                    await channel.send(final_response)
                else:
                    print(f"😴 [Agent] 決定不回覆或休眠。 (Response: {response_text})")

        except asyncio.CancelledError:
            print("🛑 [Agent] Task Cancelled (New message arrived or interruption)")
        except Exception as e:
            print(f"❌ [Agent] Critical Error: {e}")
            await channel.send(f"😵 (系統錯誤: {e})")

    @commands.group(name="status", invoke_without_command=True)
    async def status_group(self, ctx):
        memory_status = '✅ Postgres (Mem0)' if self.orchestrator.memory_service else '❌ Disabled'
        await ctx.send(f"🤖 **HiHi Agent V2**\n- Model: {self.orchestrator.model_name}\n- Memory: {memory_status}\n- Mode: Agentic Loop")

    @commands.command(name="forget_me")
    async def forget_me_command(self, ctx):
        """
        物理抹除您在「嗨嗨」記憶系統中的所有事實足跡，符合 GDPR 遺忘權。
        """
        user_id = str(ctx.author.id)
        user_name = ctx.author.name
        
        status_msg = await ctx.send(f"🧹 正在為 **{user_name}** 執行 GDPR 遺忘權，物理銷毀所有長期記憶中...")
        
        try:
            if self.orchestrator.memory_service:
                await self.orchestrator.memory_service.delete_all_user_memories(user_id)
                await status_msg.edit(content=f"🎯 **遺忘權執行完畢**！\n我已經把關於 **{user_name}** 的所有長期事實與向量完全從我的大腦中**物理抹除**了！我們現在就像初次見面一樣乾淨了喔～😊")
            else:
                await status_msg.edit(content="❌ **遺忘權執行失敗**：長期記憶體尚未開啟。")
        except Exception as e:
            await status_msg.edit(content=f"❌ **遺忘權執行失敗**：在清空長期資料庫時遇到未預期錯誤：`{e}`")

async def setup(bot):
    await bot.add_cog(AIChat(bot))
