import re
with open('/home/terraria/servers/discord_bot/cogs/ai_chat.py', 'r') as f:
    code = f.read()

# 1. 新增 heartbeat_loop 任務定義
heartbeat_task_code = """
    @tasks.loop(minutes=30)
    async def heartbeat_task(self):
        \"\"\"
        嗨嗨的生理時鐘 (內在驅動迴圈)
        每半小時執行一次，讓她在背景有事做。
        \"\"\"
        if not self.memory_manager: return
        
        # 決定是否要進行反芻 (加一點隨機性，不要每次醒來都做)
        import random
        if random.random() < 0.5:
            print("💓 [Heartbeat] 嗨嗨醒了，決定整理一下別人的印象...")
            await self._reflect_memories()
        else:
            print("💓 [Heartbeat] 嗨嗨醒了，看了看四周又繼續發呆。")

    async def _reflect_memories(self):
        \"\"\"反芻記憶：讀取隨機玩家的歷史，更新嗨嗨對他的主觀印象\"\"\"
        if not self.memory_manager: return
        try:
            # 撈出最近有發言的玩家歷史 (此處簡化為拉取近50條訊息中出現最多次的使用者)
            recent_chat = await self.memory_manager.get_recent_chat_history(limit=50)
            target_user = None
            users_seen = set()
            # 嘗試找最近講話的 user
            for msg in reversed(recent_chat):
                content = msg.get("content", "")
                if msg.get("role") == "user" and "|" in content and "[" in content:
                    # Parse user name from header "[Name (id) | ...]"
                    import re
                    match = re.search(r'\[(.*?) \((.*?)\) \|', content)
                    if match:
                        user_name = match.group(1).strip()
                        user_id = match.group(2).strip()
                        if user_id != "System":
                            target_user = (user_id, user_name)
                            break
            
            if not target_user: return
            user_id, user_name = target_user
            
            # 拿到舊印象
            old_impression = await self.memory_manager.get_user_impression(user_id)
            
            # 給 Gemini 產出新印象
            prompt = f\"\"\"
你正在腦海中回想 {user_name} 這個人。
你過去對他的印象是：「{old_impression}」

請根據他最近在你腦海裡浮現的對談畫面，重新調整你對他的看法。
請用第一人稱寫下一小段(50字內)你現在對他的整體主觀感受。
如果你覺得他很有趣、很煩、或是很無聊，都可以直接表達。
\"\"\"
            if self.client:
                response = await self.client.aio.models.generate_content(
                    model=self.model_name,
                    contents=prompt
                )
                new_impression = response.text.strip()
                if new_impression:
                    await self.memory_manager.update_user_impression(user_id, user_name, new_impression)
                    print(f"🧠 [Reflection] 嗨嗨更新了對 {user_name} 的印象！")
        except Exception as e:
            print(f"⚠️ [Reflection] 反芻錯誤: {e}")
"""

# 在 ice_breaker_task 結束（如果是檔案內某處），或直接放在類別最後。
# 因為目前沒看到 ice_breaker_task 定義，我們直接把 task 加在 _init_ai 前面
# Replace init
init_replace = """        # 啟動背景任務
        self.heartbeat_task.start()
        # Initialize AI Async
        self.bot.loop.create_task(self._init_ai())"""

code = code.replace("""        # 啟動背景任務
        self.ice_breaker_task.start()
        # Initialize AI Async
        self.bot.loop.create_task(self._init_ai())""", init_replace)

unload_replace = """    def cog_unload(self):
        self.heartbeat_task.cancel()"""

code = code.replace("""    def cog_unload(self):
        self.ice_breaker_task.cancel()""", unload_replace)

# 插入 heartbeat 方法
if "async def _init_ai" in code:
    code = code.replace("    async def _init_ai", heartbeat_task_code + "\n    async def _init_ai")

# 2. 修改 System Prompt，加入印象注入
system_prompt_def = 'async def _get_system_prompt(self, facts_context="", location_context="", knowledge_context="", self_identity=""):\n        # Emoji List'
system_prompt_def_new = 'async def _get_system_prompt(self, facts_context="", location_context="", knowledge_context="", self_identity="", impressions_context=""):\n        # Emoji List'
code = code.replace(system_prompt_def, system_prompt_def_new)

system_prompt_fact_block = """{facts_context if facts_context else "(目前沒有已知事實)"}

# ==========================================
# 【保密協定"""

system_prompt_fact_block_new = """{facts_context if facts_context else "(目前沒有客觀事實)"}

# ==========================================
# 【我對這些人的主觀印象 (My Subjective Impressions)】
# ==========================================
以下是你目前內心對剛才對話的人的情感與看法：
{impressions_context if impressions_context else "(對這些人還沒有特別的主觀印象)"}
這些印象由你過去的記憶與心情塑造，請**自然地根據這些印象**產生面對他們的態度與語氣！如果你覺得對方很煩，可以直接給他貼圖或兇他。

# ==========================================
# 【保密協定"""

code = code.replace(system_prompt_fact_block, system_prompt_fact_block_new)

# 3. 處理 msg batch 獲得印象
# Search for Facts Injection
fact_inject_block = """            # 2. Context Building (Similar to before)
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
                        facts_context = "[已知事實 (Known Facts)]\\n" + "\\n".join(facts_lines)
                except Exception as e: print(f"⚠️ Fact Injection Error: {e}")"""

fact_inject_block_new = """            # 2. Context Building (Similar to before)
            # Fact Injection & Impressions
            facts_context = ""
            impressions_context = ""
            if self.memory_manager:
                try:
                    target_users = set()
                    for msg in messages_to_process:
                        target_users.add(msg.author)
                        for user in msg.mentions:
                            if not user.bot: target_users.add(user)
                    
                    facts_lines = []
                    impression_lines = []
                    for user in target_users:
                        user_key = user.name
                        user_str_id = str(user.id)
                        
                        # 抓取客觀事實
                        user_facts = await self.memory_manager.get_facts(user_key)
                        if user_facts:
                            facts_lines.append(f"- {user.display_name} ({user.name}):")
                            for f in user_facts:
                                facts_lines.append(f"  * {f}")
                                
                        # 抓取主觀印象
                        user_imp = await self.memory_manager.get_user_impression(user_str_id, default="")
                        if user_imp:
                            impression_lines.append(f"- 對 {user.display_name} 的感覺: 「{user_imp}」")
                            
                    if facts_lines:
                        facts_context = "[客觀事實]\\n" + "\\n".join(facts_lines)
                    if impression_lines:
                        impressions_context = "\\n".join(impression_lines)
                except Exception as e: print(f"⚠️ Fact/Impression Injection Error: {e}")"""

code = code.replace(fact_inject_block, fact_inject_block_new)

# 4. 呼叫 system prompt
call_prompt = "system_prompt = await self._get_system_prompt(facts_context, location_info, knowledge_context, self_identity)"
call_prompt_new = "system_prompt = await self._get_system_prompt(facts_context, location_info, knowledge_context, self_identity, impressions_context)"
code = code.replace(call_prompt, call_prompt_new)

with open('/home/terraria/servers/discord_bot/cogs/ai_chat.py', 'w') as f:
    f.write(code)

print("完成修改 ai_chat.py")
