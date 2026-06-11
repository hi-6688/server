# -*- coding: utf-8 -*-
import os
import asyncio
from datetime import datetime, timezone, timedelta
from apscheduler import AsyncScheduler, ConflictPolicy
from apscheduler.datastores.sqlalchemy import SQLAlchemyDataStore
from apscheduler.triggers.date import DateTrigger
from sqlalchemy.ext.asyncio import create_async_engine

_global_scheduler_instance = None

async def global_execute_scheduled_wake(intent: str):
    """全域模組層級函數，避免 APScheduler 序列化綁定方法時連帶 pickle 整個 Bot 導致出錯"""
    if _global_scheduler_instance:
        await _global_scheduler_instance.execute_scheduled_wake(intent)

class HeartbeatScheduler:
    """
    定時心跳排程器 (HeartbeatScheduler)
    封裝 APScheduler 4.0 異步排程引擎，負責生命週期管理、資料庫引擎釋放、甦醒鬧鐘安排與甦醒主動對話回呼。
    """
    def __init__(self, bot, cog_instance):
        self.bot = bot
        self.cog_instance = cog_instance
        self.scheduler = None
        self.scheduler_task = None
        global _global_scheduler_instance
        _global_scheduler_instance = self
        
    async def start(self):
        """
        在背景啟動排程器的生命週期任務。
        """
        db_url = os.getenv("DATABASE_URL")
        if db_url:
            print("🔌 [Scheduler] 正在背景啟動排程任務...")
            self.scheduler_task = self.bot.loop.create_task(self.run_scheduler())
        else:
            print("⚠️ [Scheduler] 未配置 DATABASE_URL，無法啟用持久化排程器。")
 
    def stop(self):
        """
        停止排程器任務。
        """
        if self.scheduler_task:
            self.scheduler_task.cancel()
            print("🧹 [Scheduler] 背景排程任務已發出取消信號。")
 
    async def run_scheduler(self):
        """
        以背景協程方式執行 APScheduler v4.0 的 context manager，確保其生命週期與 Cog 對齊，
        並在最後 100% 物理釋放 SQLAlchemy 連線池以防洩漏。
        """
        engine = None
        try:
            db_url = os.getenv("DATABASE_URL")
            cleaned_db_url = db_url.replace("postgres://", "postgresql+asyncpg://").replace("?sslmode=require", "")
            print(f"🔌 [Scheduler] 正在初始化 SQLAlchemyDataStore 連接: {cleaned_db_url.split('@')[-1]}")
            
            engine = create_async_engine(cleaned_db_url)
            data_store = SQLAlchemyDataStore(engine)
            
            async with AsyncScheduler(data_store) as scheduler:
                self.scheduler = scheduler
                print("💓 [Scheduler] 異步排程引擎啟動成功，並已在背景持續執行！")
                await scheduler.run_until_stopped()
        except asyncio.CancelledError:
            print("🧹 [Scheduler] 背景排程任務被取消，已安全退出。")
        except Exception as e:
            print(f"❌ [Scheduler] 排程器運行出錯: {e}")
        finally:
            if engine:
                print("🔌 [Scheduler] 正在釋放 SQLAlchemy 連線池...")
                await engine.dispose()
                print("🔌 [Scheduler] SQLAlchemy 連線池已成功釋放！")
 
    async def schedule_next_sleep(self, seconds: int, intent: str = None):
        """
        使用 APScheduler v4.0 動態安排下一次心跳甦醒任務。
        """
        if not self.scheduler:
            print("⚠️ [Scheduler] 排程器未啟動，無法安排睡眠。")
            return
            
        wakeup_time = datetime.now(timezone.utc) + timedelta(seconds=seconds)
        self.cog_instance.sleep_intent = intent
        self.cog_instance.next_sleep_duration = seconds
        
        # conflict_policy=ConflictPolicy.replace 實現覆寫更新
        await self.scheduler.add_schedule(
            global_execute_scheduled_wake,
            DateTrigger(run_time=wakeup_time),
            id="hihi_heartbeat_schedule",
            args=[intent],
            conflict_policy=ConflictPolicy.replace
        )
        print(f"⏰ [Scheduler] 已安排下一次主動甦醒：{wakeup_time}。備忘錄: '{intent}'")

    async def execute_scheduled_wake(self, intent: str):
        """
        時間到後，APScheduler 自動非同步觸發此方法發起主動閒聊。
        """
        print(f"💓 [Scheduler] 鬧鐘時間到，主動甦醒中。備忘意圖: '{intent}'")
        target_channel_id = 1467980863990927623
        channel = self.bot.get_channel(target_channel_id)
        
        if not channel:
            print(f"⚠️ [Scheduler] 找不到目標頻道 {target_channel_id}，放棄主動閒聊。")
            return
            
        try:
            current_time = datetime.now(timezone(timedelta(hours=8))).strftime('%m月%d日 %H:%M')
            
            # 使用大腦編排器取得系統 System Prompt
            base_prompt = await self.cog_instance.orchestrator.get_system_prompt("", f"頻道：{channel.name}", "", "")
            
            awaken_hint = f"*(時間來到了 {current_time}。休眠結束，腦海中浮現了先前的備忘錄：「{intent}」)*" if intent else f"*(時間來到了 {current_time})*"
            location_info = f"- 伺服器 (Server): {channel.guild.name if channel.guild else '私人訊息 (Private)'}\n- 頻道 (Channel): {channel.name}"
            
            async with channel.typing():
                # 每次觸發跳時（鬧鐘響起時）背景整理最近活躍用戶的記憶 (Dream Gate)
                user_id = getattr(self.cog_instance, 'last_active_user_id', None)
                user_name = getattr(self.cog_instance, 'last_active_user_name', 'Unknown')
                if user_id:
                    try:
                        print(f"🌌 [Scheduler] 甦醒整理記憶中... 用戶: {user_name} ({user_id})")
                        await self.cog_instance.orchestrator.enter_dream_gate(user_id, user_name)
                    except Exception as e_dream:
                        print(f"⚠️ [Scheduler] 甦醒造夢整理記憶失敗: {e_dream}")

                response_text, interaction_id = await self.cog_instance.orchestrator.call_adk_runner(
                    user_id="heartbeat_awakening",
                    session_id=f"discord_{channel.id}",
                    new_message=awaken_hint,
                    system_instruction=base_prompt,
                    location_info=location_info
                )
                
                if response_text and response_text.strip() and not response_text.startswith("😵"):
                    final_response = self.cog_instance.emoji_service.replace_emojis(response_text)
                    await channel.send(final_response)
                else:
                    print("😴 [Scheduler] AI 決定繼續裝死不發言。")
        except Exception as e:
            print(f"❌ [Scheduler] 主動閒聊失敗: {e}")
