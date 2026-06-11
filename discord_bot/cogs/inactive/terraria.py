import discord
from discord.ext import commands, tasks
from discord import app_commands
from discord.ui import Button, View
import asyncio
import subprocess
import os
import re
from dotenv import load_dotenv

# Load Command Config
import json
CMD_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'conch', 'commands.json')
try:
    with open(CMD_CONFIG_PATH, 'r', encoding='utf-8') as f:
        FULL_CONFIG = json.load(f)
        CMD_CONFIG = FULL_CONFIG.get('commands', {})
        SETTINGS = FULL_CONFIG.get('settings', {})
except Exception as e:
    print(f"Error loading commands.json from data/conch/: {e}")
    CMD_CONFIG = {}
    FULL_CONFIG = {}

# Debug: Print loaded names
print(f"🔍 Loading Commands Config:")
for key, val in CMD_CONFIG.items():
    print(f"  - {key}: {val.get('name')} (Channels: {val.get('allowed_channels')})")

BOT_NAME = SETTINGS.get('server_name', "神奇嗨螺")

# Load .env (from project root)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

# Server Paths (Default to /home/terraria/servers/terraria if not set)
SERVER_DIR = os.getenv('TERRARIA_SERVER_DIR', "/home/terraria/servers/terraria")
SERVER_BIN_NAME = os.getenv('TERRARIA_BIN_NAME', "TerrariaServer.bin.x86_64")
SERVER_BIN = os.path.join(SERVER_DIR, SERVER_BIN_NAME)
SERVER_CONFIG_NAME = os.getenv('TERRARIA_CONFIG_NAME', "server_config.txt")
SERVER_CONFIG = os.path.join(SERVER_DIR, SERVER_CONFIG_NAME)

# Settings
IDLE_TIMEOUT = int(os.getenv('TERRARIA_IDLE_TIMEOUT', 10))

# --- REGEX PATTERNS ---
JOIN_PATTERN = re.compile(r'(?:.*:\s)?(.+) has joined\.')
LEFT_PATTERN = re.compile(r'(?:.*:\s)?(.+) has left\.')
CHAT_PATTERN = re.compile(r'<(.+?)> (.*)')

# --- HELPERS ---
def get_public_ip():
    try:
        # Simple external call to get public IP, fallback to placeholder
        cmd = "curl -s ifconfig.me"
        result = subprocess.check_output(cmd, shell=True, timeout=2).decode('utf-8').strip()
        return result
    except:
        return "127.0.0.1"

class HistoryView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="📜 查看歷史紀錄", style=discord.ButtonStyle.secondary, custom_id="history_btn")
    async def show_history(self, interaction: discord.Interaction, button: Button):
        history_text = """
        **📜 神奇嗨螺的回憶錄**
        ---------------------
        **v2.0 重構版**
        - 優化核心架構，移除實驗性功能。
        - 增強環境變數支援。
        """
        await interaction.response.send_message(history_text, ephemeral=True)

class Terraria(commands.Cog):
    """Terraria 伺服器管理模組"""

    def __init__(self, bot):
        self.bot = bot
        self.server_process = None
        self.server_task = None
        self.player_count = 0
        self.empty_minutes = 0
        self.chat_channel = None
        
        # Load Env specific to this module
        self.channel_id = int(os.getenv('TERRARIA_CHANNEL_ID', '0'))
        self.log_channel_id = int(os.getenv('DISCORD_LOG_CHANNEL_ID', '0'))
        self.log_channel = None

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'⚙️ Terraria 模組已就緒 (Game: {self.channel_id}, Log: {self.log_channel_id})')
        self.chat_channel = self.bot.get_channel(self.channel_id)
        self.log_channel = self.bot.get_channel(self.log_channel_id)

        if not self.check_idle_loop.is_running():
            self.check_idle_loop.start()

    @tasks.loop(minutes=1)
    async def check_idle_loop(self):
        if not self.server_process:
            # Auto-discovery: Check if server is running (started by Test Bot)
            if await self.is_screen_running():
                print("[INFO] Discovered running server! Attaching monitor...")
                self.server_process = "SCREEN_SESSION"
                if not self.server_task or self.server_task.done():
                    self.server_task = self.bot.loop.create_task(self.read_output())
            return 

        if self.player_count == 0:
            self.empty_minutes += 1
        else:
            self.empty_minutes = 0 
            
        # Auto-shutdown (Optional, disabled for now or check setting)
        pass

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return

        # 依然只處理特定頻道
        if message.channel.id != self.channel_id:
            return

    async def verify_permission(self, interaction: discord.Interaction, command_key: str) -> bool:
        """
        檢查權限並回傳錯誤訊息 (Async)
        如果權限不足，會自動發送 ephemeral 訊息。
        回傳 True 代表通過，False 代表被拒絕。
        """
        cmd_setting = CMD_CONFIG.get(command_key, {})
        allowed_names = cmd_setting.get('allowed_channels', [])
        
        channel_map = FULL_CONFIG.get('channels', {})
        allowed_ids = []
        for name in allowed_names:
            str_id = channel_map.get(name)
            if str_id:
                try:
                    allowed_ids.append(int(str_id))
                except:
                    pass
        
        if not allowed_ids:
            return True # 沒設定限制則允許

        if interaction.channel_id in allowed_ids:
            return True

        # --- 權限不足：產生錯誤訊息 ---
        if allowed_names == ["後台管理頻道"]:
             msg = "無功能，開發者用，會看到是因為你是DC管理員"
        else:
             msg = f"⛔ 權限不足！此指令僅限於以下頻道使用：\n" + "\n".join([f"- {n}" for n in allowed_names])
        
        await interaction.response.send_message(msg, ephemeral=True)
        return False

    @app_commands.command(
        name=CMD_CONFIG.get('status', {}).get('name', 'status'),
        description=CMD_CONFIG.get('status', {}).get('description', 'Show status')
    )
    async def slash_status(self, interaction: discord.Interaction):
        if not await self.verify_permission(interaction, 'status'):
             return
        
        # Defer immediately to prevent timeout
        await interaction.response.defer()
        
        # On-demand Check: If we think it's offline, check screen just in case
        if not self.server_process:
             if await self.is_screen_running():
                 self.server_process = "SCREEN_SESSION"
                 if not self.server_task or self.server_task.done():
                    self.server_task = self.bot.loop.create_task(self.read_output())

        ip = get_public_ip()
        if self.server_process:
            await interaction.followup.send(f"✅ **線上** | 🌍 `{ip}:7777` | 👥 線上: {self.player_count}人")
        else:
            await interaction.followup.send(f"🔴 **離線** | 請呼叫 **測試雞** 使用 `/泰亂啟動`")


    async def run_terraria_server(self):
        self.empty_minutes = 0
        
        # Ensure channels are initialized (fallback if on_ready hasn't run yet)
        if not self.chat_channel:
            self.chat_channel = self.bot.get_channel(self.channel_id)
        if not self.log_channel:
            self.log_channel = self.bot.get_channel(self.log_channel_id)
        
        print(f"[DEBUG run_terraria_server] chat_channel: {self.chat_channel}, log_channel: {self.log_channel}")
        
        # Dev Mode Safety Check
        is_dev = SETTINGS.get('dev_mode', False)
        if is_dev:
            print("[DEV] 模擬啟動伺服器... (不會真的執行)")
            if self.chat_channel:
                await self.send_log(content=f"🧪 [測試模式] 模擬啟動程序完成。真實伺服器未受影響。")
            self.server_process = "FAKE_PROCESS"
            self.player_count = 999
            await self.update_status()
            return

        # Check if already running via screen (use .terraria to match session name format PID.terraria)
        check_screen = await asyncio.create_subprocess_shell(
            "screen -list | grep '\\.terraria'",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, _ = await check_screen.communicate()
        if stdout:
            print("Server already running in screen session 'terraria'")
            if self.chat_channel:
                await self.send_log("⚠️ 伺服器已經在 Screen 中運行！(我已自動重新連接監控)")
            # Re-attach logic
            self.server_process = "SCREEN_SESSION" 
            if not self.server_task or self.server_task.done():
                self.server_task = self.bot.loop.create_task(self.read_output())
            return

        # Start Screen Session (Native Logging)
        log_file = os.path.join(SERVER_DIR, "server.log")
        
        # Truncate log file for clean start
        with open(log_file, 'w') as f: f.write("")
        
        screen_cmd = [
            "screen", "-dmS", "terraria",
            "-L", "-Logfile", log_file,
            SERVER_BIN, "-config", SERVER_CONFIG
        ]
        
        print(f"Starting server in screen: {screen_cmd}")
        if self.chat_channel:
             await self.send_log(content=f"🟢 {BOT_NAME} 正在啟動伺服器 (Screen mode)...", view=HistoryView())

        try:
            process = await asyncio.create_subprocess_exec(
                *screen_cmd,
                cwd=SERVER_DIR
            )
            await process.wait()
            
            # Force log flush to ensure immediate visibility
            try:
                await asyncio.sleep(1)
                flush_cmd = ["screen", "-S", "terraria", "-X", "logfile", "flush", "0"]
                await asyncio.create_subprocess_exec(*flush_cmd)
            except:
                pass
            
            self.server_process = "SCREEN_SESSION"
            # Start background reader task (Fresh start, read from beginning)
            self.server_task = self.bot.loop.create_task(self.read_output(from_start=True))
            
        except Exception as e:
            print(f"Failed to start screen: {e}")
            if self.chat_channel:
                 await self.send_log(f"❌ 啟動失敗: {e}") 

    async def read_output(self, from_start=False):
        """Monitor server.log for output"""
        log_path = os.path.join(SERVER_DIR, "server.log")
        print(f"Started log monitor: {log_path} (From start: {from_start})")
        
        if not os.path.exists(log_path):
            with open(log_path, 'w') as f: f.write("")
            
        try:
            with open(log_path, 'r', encoding='utf-8', errors='replace') as f:
                if not from_start:
                    f.seek(0, 2) # Go to end only if re-attaching
                else:
                    f.seek(0, 0) # Start from beginning if fresh start
                
                while self.server_process == "SCREEN_SESSION":
                    line = f.readline()
                    if not line:
                        await asyncio.sleep(0.5)
                        if not await self.is_screen_running():
                            print("Screen session ended.")
                            self.server_process = None
                            if self.chat_channel:
                                await self.send_log("🔴 伺服器 Screen Session 已結束。")
                            await self.update_status()
                            break
                        continue
                        
                    line = line.strip()
                    if not line: continue
                    print(f"[LOG] {line}")
                    await self.parse_output(line)
        except Exception as e:
            print(f"Log monitor error: {e}")
    
    async def is_screen_running(self):
        try:
            proc = await asyncio.create_subprocess_shell(
                "screen -list | grep '\\.terraria'",
                stdout=asyncio.subprocess.PIPE
            )
            stdout, _ = await proc.communicate()
            return bool(stdout)
        except:
            return False

    async def send_log(self, content=None, view=None):
        target = self.log_channel if self.log_channel else self.chat_channel
        if target:
            await target.send(content=content, view=view)

    async def parse_output(self, line):
        # Handle system messages FIRST (these go to log_channel, not chat_channel)
        if "Server started" in line:
             print(f"[DEBUG] Detected 'Server started' in line: {line}")
             print(f"[DEBUG] log_channel: {self.log_channel}, chat_channel: {self.chat_channel}")
             await self.send_log(f"✅ 伺服器啟動完成！使用 `/泰亂狀態` 查看狀態。")
             print(f"[DEBUG] send_log completed for Server started")
             await self.update_status()
             return
        
        # For player messages, chat_channel is required
        if not self.chat_channel:
            # Don't spam logs for every line
            if "Server" in line or "started" in line:
                print(f"[DEBUG parse_output] chat_channel is None! Skipping line: {line[:50]}")
            return
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

    async def update_status(self):
        activity = discord.Activity(type=discord.ActivityType.playing, name=f"Terraria | {self.player_count}人")
        await self.bot.change_presence(activity=activity)

    async def send_command(self, cmd):
        if self.server_process == "FAKE_PROCESS":
             print(f"[DEV] Fake Command Sent: {cmd}")
             return

        print(f"Sending to screen: {cmd}")
        try:
            # \r simulates Enter
            full_cmd = f"{cmd}\r"
            proc = await asyncio.create_subprocess_exec(
                "screen", "-S", "terraria", "-X", "stuff", full_cmd
            )
            await proc.wait()
        except Exception as e:
            print(f"Failed to send command to screen: {e}")

async def setup(bot):
    await bot.add_cog(Terraria(bot))
