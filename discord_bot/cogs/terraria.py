import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View
import asyncio
import subprocess
import os
import re
from dotenv import load_dotenv

# --- CONFIGURATION (Adapted for Cog) ---
# 這些路徑必須改成絕對路徑，因為 bot 執行位置變了
SERVER_DIR = "/home/terraria/servers/terraria"
SERVER_BIN = os.path.join(SERVER_DIR, "TerrariaServer.bin.x86_64")
SERVER_CONFIG = os.path.join(SERVER_DIR, "server_config.txt")
IDLE_TIMEOUT = 10 

# --- VERSION INFO ---
BOT_NAME = "🐚 神奇嗨螺"
SERVER_IP = "34.81.50.240"
SERVER_PORT = "7777"

CHANGELOG_CURRENT = f"""
# 🚀 伺服器大更新！v1.4.5 @ 2026

**🎉 Terraria 1.4.5 (Bigger and Boulder) 正式上線！**

**🌍 新世界開放：泰亂四福氣**
- **設定**: 大型 (Large) / 經典 (Classic)
- **語言**: 支援繁體中文 (zh-TW)
- **IP**: `{SERVER_IP}`
- **Port**: `{SERVER_PORT}`

**✨ 更新重點**:
- 全新變身坐騎、Dead Cells / Palworld 連動內容。
- 詳細更新內容請見官方公告。

*「冒險現在才開始！快進來探索吧！」*
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

class HistoryView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 查看歷史紀錄", style=discord.ButtonStyle.secondary, custom_id="history_btn")
    async def show_history(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_message(HISTORY_TEXT, ephemeral=True)

class Terraria(commands.Cog):
    """Terraria 伺服器管理模組"""

    def __init__(self, bot):
        self.bot = bot
        self.server_process = None
        self.server_task = None
        self.player_count = 0
        self.empty_minutes = 0
        self.chat_channel = None
        
        # Load Env specific to this module if needed, or rely on main
        load_dotenv()
        try:
            self.channel_id = int(os.getenv('DISCORD_CHANNEL_ID', '0'))
        except:
            self.channel_id = 0

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'⚙️ Terraria 模組已就緒 (Channel ID: {self.channel_id})')
        self.chat_channel = self.bot.get_channel(self.channel_id)

        if not self.check_idle_loop.is_running():
            self.check_idle_loop.start()

        # 自動啟動伺服器相關任務 (如果有需要)
        # 這裡我們不自動啟動伺服器，等待指令
        # if not self.server_task:
        #     self.server_task = self.bot.loop.create_task(self.run_terraria_server())

    @tasks.loop(minutes=1)
    async def check_idle_loop(self):
        if not self.server_process:
            return 

        if self.player_count == 0:
            self.empty_minutes += 1
            # print(f"[AutoSaver] 閒置計時: {self.empty_minutes}/{IDLE_TIMEOUT}")
            
            # [DISABLED] User requested to disable auto-shutdown
            # if self.empty_minutes >= IDLE_TIMEOUT:
            #     if self.chat_channel:
            #         await self.chat_channel.send(f"💤 已經沒有人了... {BOT_NAME} 決定去休息了。(自動關機)")
            #     await self.send_command("exit") 
            #     self.empty_minutes = 0 
        else:
            self.empty_minutes = 0 

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author == self.bot.user:
            return

        # 依然只處理特定頻道
        if message.channel.id != self.channel_id:
            return
        
        # 聊天轉發 Discord -> Terraria
        # if self.server_process and not message.content.startswith('/'):
        #     # 檢查是否為指令 (有些 bot framework 會先處理指令，這裡再次過濾保險)
        #     if message.content.startswith(self.bot.command_prefix): 
        #         return
        #
        #     clean_msg = message.content.replace('\n', ' ').replace('"', "'")
        #     author = message.author.display_name
        #     cmd = f'say [DC] {author}: {clean_msg}'
        #     await self.send_command(cmd)

    async def run_terraria_server(self):
        self.empty_minutes = 0 
        cmd = [SERVER_BIN, "-config", SERVER_CONFIG]
        
        # 確保有執行權限
        try:
            os.chmod(SERVER_BIN, 0o755)
        except Exception as e:
            print(f"Warning: Could not chmod server bin: {e}")

        print(f"Starting server with: {' '.join(cmd)}")
        try:
            self.server_process = await asyncio.create_subprocess_exec(
                *cmd,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.STDOUT,
                cwd=SERVER_DIR # 設定工作目錄為伺服器目錄
            )
        except Exception as e:
            print(f"Failed to start server: {e}")
            if self.chat_channel:
                 await self.chat_channel.send(f"❌ 啟動失敗: {e}")
            return

        if self.chat_channel:
            await self.chat_channel.send(content=f"🟢 {BOT_NAME} 正在啟動伺服器...", view=HistoryView())

        while True:
            if self.server_process.stdout:
                line_bytes = await self.server_process.stdout.readline()
            else:
                break
                
            if not line_bytes: break
            try:
                line = line_bytes.decode('utf-8', errors='ignore').strip()
            except: continue
            if not line: continue

            print(f"[TR] {line}")
            await self.parse_output(line)

        if self.chat_channel:
            await self.chat_channel.send(f"🔴 伺服器已關閉。請使用 `/start` 來喚醒我。")
        self.server_process = None
        self.player_count = 0 
        self.server_task = None # 重置 task

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
        await self.bot.change_presence(activity=activity)

    async def send_command(self, cmd):
        if self.server_process and self.server_process.stdin:
            try:
                self.server_process.stdin.write(f"{cmd}\n".encode())
                await self.server_process.stdin.drain()
            except Exception as e:
                print(f"Failed to send command: {e}")

    # --- Commands ---

    @app_commands.command(name="cmd", description="發送後台指令 (例如 save, kick)")
    @app_commands.describe(command_text="要執行的指令內容")
    async def slash_cmd(self, interaction: discord.Interaction, command_text: str):
        if self.server_process:
            await self.send_command(command_text)
            await interaction.response.send_message(f"已發送指令: `{command_text}`")
        else:
            await interaction.response.send_message("伺服器休息中。", ephemeral=True)

    @app_commands.command(name="status", description="查看伺服器狀態與人數")
    async def slash_status(self, interaction: discord.Interaction):
        if self.server_process:
            await interaction.response.send_message(f"✅ {BOT_NAME} 監控中 | 🌍 `{SERVER_IP}:{SERVER_PORT}` | 線上: {self.player_count}人")
        else:
            await interaction.response.send_message("🔴 伺服器休息中。", ephemeral=True)

    @app_commands.command(name="start", description="喚醒泰拉瑞亞伺服器")
    async def slash_start(self, interaction: discord.Interaction):
        if self.server_process:
            await interaction.response.send_message("伺服器已經在運作了！", ephemeral=True)
        else:
            await interaction.response.send_message(f" {BOT_NAME} 正在召喚伺服器...")
            if self.server_task and not self.server_task.done(): 
                 pass
            # Schedule the server run task
            self.server_task = self.bot.loop.create_task(self.run_terraria_server())

async def setup(bot):
    await bot.add_cog(Terraria(bot))
