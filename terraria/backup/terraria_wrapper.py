import asyncio
import re
import os
import sys
import subprocess
import discord
from discord import app_commands
from discord.ext import commands, tasks
from discord.ui import Button, View
from datetime import datetime
from dotenv import load_dotenv

# --- CONFIGURATION ---
# Load .env explicitly
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))

TOKEN = os.getenv('DISCORD_BOT_TOKEN')
try:
    CHANNEL_ID = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
except:
    CHANNEL_ID = 0
SERVER_BIN = "./TerrariaServer.bin.x86_64"
SERVER_CONFIG = "./server_config.txt"
IDLE_TIMEOUT = 10 

# --- VERSION INFO ---
BOT_NAME = "🐚 神奇嗨螺"
VERSION = "v1.5 (斜線指令版)"
SERVER_IP = "34.81.50.240"
SERVER_PORT = "7777"

CHANGELOG_CURRENT = f"""
**🌍 泰拉瑞亞伺服器資訊**
IP: `{SERVER_IP}`
Port: `{SERVER_PORT}`

**🎉 神奇嗨螺 進化了！ (v1.5)**
============================
1. **🪄 斜線指令 (Slash Commands)**: 
   - 告別 `!` 驚嘆號！現在請使用 `/` 來呼叫我。
   - 試試看 `/status`, `/start`, `/cmd`。
   - 打字時會有自動提示，不用再怕打錯指令了！
2. **⚡ 即時同步**: 
   - 機器人啟動時會自動把指令註冊到這個伺服器。
============================
*「我可以問你問題嗎？」『試試看用斜線。』*
"""

HISTORY_TEXT = """
**📜 神奇嗨螺的回憶錄**
---------------------
**v1.5 斜線指令版**
- 全面支援 Discord Slash Commands (/)。

**v1.4 神奇嗨螺**
- 更名與互動按鈕。

**v1.3 節能版**
- 新增閒置 10 分鐘自動關機。

**v1.2 修正版**
- 修正聊天回音與人數顯示問題。

**v1.1 聊天互通**
- 實現遊戲與 Discord 雙向聊天。

**v1.0 初始版**
- 基礎監控與指令功能。
"""

# --- REGEX PATTERNS ---
JOIN_PATTERN = re.compile(r'(?:.*:\s)?(.+) has joined\.')
LEFT_PATTERN = re.compile(r'(?:.*:\s)?(.+) has left\.')
CHAT_PATTERN = re.compile(r'<(.+?)> (.*)')

# --- UI VIEWS ---
class HistoryView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 查看歷史紀錄", style=discord.ButtonStyle.secondary, custom_id="history_btn")
    async def show_history(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(HISTORY_TEXT, ephemeral=True)

class TerrariaBot(commands.Bot):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        super().__init__(command_prefix="!", intents=intents)
        self.server_process = None
        self.server_task = None
        self.player_count = 0
        self.empty_minutes = 0
        self.chat_channel = None

    async def setup_hook(self):
        # 這裡不進行全域同步，改在 on_ready 針對單一伺服器同步，速度更快
        pass

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        self.chat_channel = self.get_channel(CHANNEL_ID)
        
        # [NEW] 自動同步斜線指令到目前的伺服器 (Guild)
        if self.chat_channel and self.chat_channel.guild:
            guild = self.chat_channel.guild
            print(f"Detected Guild: {guild.name} (ID: {guild.id})")
            self.tree.copy_global_to(guild=guild)
            await self.tree.sync(guild=guild)
            print("Slash commands synced to guild!")

        if not self.check_idle_loop.is_running():
            self.check_idle_loop.start()

        if self.chat_channel:
            await self.chat_channel.send(content=CHANGELOG_CURRENT, view=HistoryView())
        
        if not self.server_task:
            self.server_task = self.loop.create_task(self.run_terraria_server())

    @tasks.loop(minutes=1)
    async def check_idle_loop(self):
        if not self.server_process:
            return 

        if self.player_count == 0:
            self.empty_minutes += 1
            print(f"[AutoSaver] 閒置計時: {self.empty_minutes}/{IDLE_TIMEOUT}")
            
            if self.empty_minutes >= IDLE_TIMEOUT:
                if self.chat_channel:
                    await self.chat_channel.send(f"💤 已經沒有人了... {BOT_NAME} 決定去休息了。(自動關機)")
                await self.send_command("exit") 
                self.empty_minutes = 0 
        else:
            self.empty_minutes = 0 

    async def on_message(self, message):
        if message.author == self.user:
            return

        # 依然只處理特定頻道
        if message.channel.id != CHANNEL_ID:
            return

        # 如果是指令 (/) 開頭，discord.py 會自動忽視 on_message ?? 
        # 不一定，但這裡我們主要處理「聊天轉發」
        # 斜線指令由 app_commands 處理，不會撞車
        
        # 聊天轉發 Discord -> Terraria
        if self.server_process and not message.content.startswith('/'):
            clean_msg = message.content.replace('\n', ' ').replace('"', "'")
            author = message.author.display_name
            cmd = f'say [DC] {author}: {clean_msg}'
            await self.send_command(cmd)

    async def run_terraria_server(self):
        self.empty_minutes = 0 
        cmd = [SERVER_BIN, "-config", SERVER_CONFIG]
        os.chmod(SERVER_BIN, 0o755)
        print(f"Starting server with: {' '.join(cmd)}")
        self.server_process = await asyncio.create_subprocess_exec(
            *cmd,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.STDOUT
        )

        while True:
            line_bytes = await self.server_process.stdout.readline()
            if not line_bytes: break
            try:
                line = line_bytes.decode('utf-8', errors='ignore').strip()
            except: continue
            if not line: continue

            print(f"[TR] {line}")
            await self.parse_output(line)

        await self.chat_channel.send(f"🔴 伺服器已關閉。請使用 `/start` 來喚醒我。")
        self.server_process = None
        self.player_count = 0 

    async def parse_output(self, line):
        if not self.chat_channel: return
        if "[DC]" in line: return

        join_match = JOIN_PATTERN.search(line)
        if join_match:
            player_name = join_match.group(1)
            self.player_count += 1
            self.empty_minutes = 0 
            await self.update_status()
            await self.chat_channel.send(f"🟢 **{player_name}** 加入了遊戲 (線上: {self.player_count}人)")
            return

        left_match = LEFT_PATTERN.search(line)
        if left_match:
            player_name = left_match.group(1)
            self.player_count = max(0, self.player_count - 1)
            await self.update_status()
            await self.chat_channel.send(f"👋 **{player_name}** 離開了遊戲 (線上: {self.player_count}人)")
            return

        chat_match = CHAT_PATTERN.search(line)
        if chat_match:
            user, msg = chat_match.groups()
            await self.chat_channel.send(f"**<{user}>** {msg}")

        if "Server started" in line:
             await self.chat_channel.send(f"✅ 伺服器啟動完成！讚美 {BOT_NAME}！")
             await self.update_status()

    async def update_status(self):
        activity = discord.Activity(type=discord.ActivityType.playing, name=f"Online: {self.player_count}人")
        await self.change_presence(activity=activity)

    async def send_command(self, cmd):
        if self.server_process and self.server_process.stdin:
            self.server_process.stdin.write(f"{cmd}\n".encode())
            await self.server_process.stdin.drain()

bot = TerrariaBot()

# --- SLASH COMMANDS DEFINITION ---

@bot.tree.command(name="cmd", description="發送後台指令 (例如 save, kick)")
@app_commands.describe(command_text="要執行的指令內容")
async def slash_cmd(interaction: discord.Interaction, command_text: str):
    if bot.server_process:
        await bot.send_command(command_text)
        await interaction.response.send_message(f"已發送指令: `{command_text}`")
    else:
        await interaction.response.send_message("伺服器休息中。", ephemeral=True)

@bot.tree.command(name="status", description="查看伺服器狀態與人數")
async def slash_status(interaction: discord.Interaction):
    if bot.server_process:
        await interaction.response.send_message(f"✅ {BOT_NAME} 監控中 | 🌍 `{SERVER_IP}:{SERVER_PORT}` | 線上: {bot.player_count}人")
    else:
        await interaction.response.send_message("🔴 伺服器休息中。", ephemeral=True)

@bot.tree.command(name="start", description="喚醒泰拉瑞亞伺服器")
async def slash_start(interaction: discord.Interaction):
    if bot.server_process:
        await interaction.response.send_message("伺服器已經在運作了！", ephemeral=True)
    else:
        await interaction.response.send_message(f" {BOT_NAME} 正在召喚伺服器...")
        if bot.server_task and not bot.server_task.done(): 
             pass
        bot.server_task = bot.loop.create_task(bot.run_terraria_server())

if __name__ == "__main__":
    if not TOKEN:
        print("Error: Token not set")
        sys.exit(1)
    # 取消一般的 command prefix 處理，只用 Slash Commands
    bot.run(TOKEN)
