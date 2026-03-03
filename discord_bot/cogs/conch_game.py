import discord
from discord import app_commands, ui
from discord.ext import commands
from google import genai
from google.genai import types
import os
import re
import enum
import time

# 定義 Structured Output 的 Enum (結構化回應)
# 這會強制 Gemini 只能回傳這四個值之一
class ConchVerdict(enum.Enum):
    YES = "YES"
    NO = "NO"
    IRRELEVANT = "IRRELEVANT"
    WIN = "WIN"

class SetAnswerModal(ui.Modal, title="設定神奇嗨螺謎底"):
    answer = ui.TextInput(
        label="謎底是什麼？",
        style=discord.TextStyle.short,
        placeholder="例如：蘋果、電腦、天空...",
        required=True,
        max_length=50
    )

    def __init__(self, cog):
        super().__init__()
        self.cog = cog

    async def on_submit(self, interaction: discord.Interaction):
        ans = self.answer.value.strip()
        
        # 驗證：不能只包含 Emoji (至少要有一個中文/英文/數字)
        if not re.search(r'[\u4e00-\u9fa5a-zA-Z0-9]', ans):
            await interaction.response.send_message("❌ 謎底必須包含文字，不能只有表情符號！", ephemeral=True)
            return

        # 設定遊戲狀態
        self.cog.start_game(interaction.channel_id, ans, interaction.user)
        
        await interaction.response.send_message(f"🔮 遊戲開始！謎底已設定 (由 {interaction.user.display_name} 發起)。\n請大家開始提問！", ephemeral=False)

class ConchGame(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.active_games = {} # {channel_id: {"answer": str, "starter": user}}
        
        # 設定 Gemini API
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            print("❌ [ConchGame] 未設定 GEMINI_API_KEY，模組無法正常運作。")
            self.client = None
            return
            
        try:
            self.client = genai.Client(api_key=api_key)
            print("🐚 [ConchGame] 模組已載入 (Client: google.genai, Model: models/gemini-2.5-flash)")
        except Exception as e:
            print(f"❌ [ConchGame] Client 初始化失敗: {e}")

    def start_game(self, channel_id, answer, starter):
        self.active_games[channel_id] = {
            "answer": answer,
            "starter": starter
        }
        print(f"🎮 [ConchGame] New game started in {channel_id}: {answer}")

    @app_commands.command(name="猜謎", description="神奇嗨螺猜詞遊戲指令")
    @app_commands.describe(action="開始: 設定謎底開始遊戲 | 結束: 公布謎底結束遊戲")
    @app_commands.choices(action=[
        app_commands.Choice(name="開始", value="start"),
        app_commands.Choice(name="結束", value="stop")
    ])
    async def guess_game(self, interaction: discord.Interaction, action: app_commands.Choice[str]):
        """神奇嗨螺遊戲控制"""
        print(f"🐚 [ConchGame] Command received: /猜謎 {action.value} from {interaction.user}")
        
        if action.value == "start":
            if interaction.channel_id in self.active_games:
                await interaction.response.send_message("❌ 這個頻道已經有一場遊戲正在進行中！請先結束 (`/猜謎 結束`)。", ephemeral=True)
                return
            await interaction.response.send_modal(SetAnswerModal(self))
            
        elif action.value == "stop":
            if interaction.channel_id not in self.active_games:
                await interaction.response.send_message("❌ 目前沒有正在進行的遊戲。", ephemeral=True)
                return
            
            game_data = self.active_games.pop(interaction.channel_id)
            answer = game_data["answer"]
            await interaction.response.send_message(f"🛑 遊戲已強制結束！\n謎底是：**{answer}**", ephemeral=False)

    @commands.Cog.listener()
    async def on_message(self, message):
        # 1. 基本過濾 (允許嗨嗨機器人參與猜謎)
        HIHI_BOT_ID = 1468584012174987274
        if message.author.bot and message.author.id != HIHI_BOT_ID: return
        # 如果機器人沒有 API 客戶端，直接退出
        if not self.client: return
        
        # 判斷頻道 (包含 Thread 支援)
        channel_id = message.channel.id
        # 如果是 Thread，嘗試獲取 parent channel ID
        if isinstance(message.channel, discord.Thread):
            channel_id = message.channel.parent_id
            
        if channel_id not in self.active_games: return
        
        if message.content.startswith(self.bot.command_prefix): return # 忽略指令
        if message.content.startswith("/"): return # 忽略 Slash Commands
        
        # 使用 await 改回同步處理 (避免並發導致的可能的 Queue 排隊延遲)
        # 用戶回饋並發反而變慢，改回循序處理
        await self._process_message(message)

    async def _process_message(self, message):
        channel_id = message.channel.id
        if isinstance(message.channel, discord.Thread):
            channel_id = message.channel.parent_id
            
        # 2. 取得遊戲資料 (再次確認遊戲是否結束)
        if channel_id not in self.active_games: return
        
        game_data = self.active_games[channel_id]
        answer = game_data["answer"]
        
        print(f"🐚 [ConchGame] Processing: {message.content} (Ans: {answer})")

        # 3. 建構 Prompt (極簡化，因為 Structured Output 會約束回應格式)
        prompt = f"Answer: {answer}\nQuestion: {message.content}"
        
        try:
            start_time = time.time()
            
            async with message.channel.typing():
                # 4. 呼叫 Gemini AI (使用 Structured Output)
                # response_mime_type + response_schema 強制模型只能回傳 Enum 中的值
                response = await self.client.aio.models.generate_content(
                    model="models/gemini-2.5-flash",
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="text/x.enum",
                        response_schema=ConchVerdict,
                        system_instruction="""You are the judge of a 20 Questions guessing game. Players are trying to guess the secret Answer.

JUDGING RULES:

1. YES/NO QUESTIONS (about properties, categories, or relationships):
   When a player asks about a property, category, or relationship of the Answer, judge whether it is TRUE.
   Be INCLUSIVE about relationships: if the Answer is RELATED to what the player asks, answer YES.
   Examples:
   - Answer=豬肉(pork), Q=是豬嗎(is it pig?) → YES (pork comes from pig, closely related)
   - Answer=豬肉(pork), Q=是食物嗎(is it food?) → YES
   - Answer=蘋果(apple), Q=是水果嗎(is it fruit?) → YES
   - Answer=蘋果(apple), Q=是紅色嗎(is it red?) → YES
   - Answer=豬肉(pork), Q=是蔬菜嗎(is it vegetable?) → NO

2. GUESS ATTEMPTS (player tries to name the answer):
   Only respond WIN if the guess is the SAME THING as the Answer (synonyms and typos OK).
   If the guess is CLOSE but NOT the same thing, respond NO.
   Examples:
   - Answer=豬肉, Q=豬排 → NO (pork chop ≠ pork, different form)
   - Answer=豬肉, Q=豬肉 → WIN
   - Answer=蘋果, Q=蘋果 → WIN

3. If the message makes no sense or is not a question/guess → IRRELEVANT""",
                        temperature=0.0  # 確定性回答，不需要隨機性
                    )
                )
                result = response.text.strip().upper()
                
            latency = (time.time() - start_time) * 1000
            print(f"🐚 [ConchGame] AI Result: {result} (Latency: {latency:.2f}ms)")
            
            # 5. 處理回應 (Structured Output 保證只有這四種值)
            reply_text = ""
            if "WIN" in result:
                reply_text = f"🎉 **恭喜答對！**\n謎底就是：**{answer}**\n(遊戲結束)"
                if channel_id in self.active_games:
                    del self.active_games[channel_id]
            elif "YES" in result:
                reply_text = "⭕ 是"
            elif "NO" in result:
                reply_text = "❌ 否"
            elif "IRRELEVANT" in result:
                reply_text = "🤷 與此無關"
            else:
                reply_text = "🤷 與此無關"
            
            if reply_text:
                await message.reply(reply_text)
                
        except Exception as e:
            print(f"⚠️ [ConchGame] AI Error: {e}")
            # 出錯時給予預設回應，避免無聲
            try:
                await message.reply("🤷 與此無關")
            except:
                pass

async def setup(bot):
    await bot.add_cog(ConchGame(bot))
