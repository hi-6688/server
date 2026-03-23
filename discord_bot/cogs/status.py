import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load Command Config
import json
# Load Command Config
import json
CMD_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data', 'conch', 'commands.json')
try:
    with open(CMD_CONFIG_PATH, 'r', encoding='utf-8') as f:
        FULL_CONFIG = json.load(f)
        CMD_CONFIG = FULL_CONFIG.get('commands', {})
except Exception as e:
    print(f"Error loading commands.json: {e}")
    CMD_CONFIG = {}
    FULL_CONFIG = {}

class Status(commands.Cog):
    """系統狀態與管理指令"""

    def __init__(self, bot):
        self.bot = bot
        # Ensure env is loaded
        env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env')
        load_dotenv(env_path)
        self.log_channel_id = int(os.getenv('DISCORD_LOG_CHANNEL_ID', '0'))
        
        # Load Admin Channel ID for IPC Security
        admin_channel_str = FULL_CONFIG.get('channels', {}).get('後台管理頻道', '0')
        self.admin_channel_id = int(admin_channel_str) if admin_channel_str else 0
        
        # Determine Bot Name based on BOT_MODE
        mode = os.getenv('BOT_MODE', 'ALL').upper()
        if mode == 'HIHI':
            self.bot_name = "嗨嗨"
        elif mode == 'CONCH':
            self.bot_name = "神奇嗨螺"
        else:
            self.bot_name = "機器人"

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'✅ Status Cog Loaded. Bot: {self.bot.user}')
        
        # [Debug] List Application Emojis (Not Guild Emojis)
        print("====== 🎪 Application Emojis 🎪 ======")
        try:
            app_emojis = await self.bot.fetch_application_emojis()
            for emoji in app_emojis:
                print(f"App Emoji: {emoji.name} -> <:{emoji.name}:{emoji.id}> (Animated: {emoji.animated})")
        except Exception as e:
            print(f"❌ Failed to fetch application emojis: {e}")
            
        print("====== 🎪 Guild Emojis 🎪 ======")
        for guild in self.bot.guilds:
            print(f"Guild: {guild.name}")
            for emoji in guild.emojis:
                print(f"Emoji: {emoji.name} -> <:{emoji.name}:{emoji.id}> (Animated: {emoji.animated})")
        print("================================")
        self.log_channel = self.bot.get_channel(self.log_channel_id)
        if self.log_channel:
            # 發送啟動訊息
            embed = discord.Embed(title=f"🤖 {self.bot_name}已重啟", description="設定檔已重新載入！指令列表已更新。", color=0x00ff00)
            await self.log_channel.send(embed=embed)

    async def verify_permission(self, interaction: discord.Interaction, command_key: str) -> bool:
        """檢查權限並回傳錯誤訊息 (Async)"""
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
            return True 

        if interaction.channel_id in allowed_ids:
            return True

        # Error Message Logic
        if allowed_names == ["後台管理頻道"]:
             msg = "無功能，開發者用，會看到是因為你是DC管理員"
        else:
             msg = f"⛔ 權限不足！此指令僅限於以下頻道使用：\n" + "\n".join([f"- {n}" for n in allowed_names])
             
        await interaction.response.send_message(msg, ephemeral=True)
        return False



    @commands.Cog.listener()
    async def on_message(self, message):
        # IPC Listener
        # Ignore self
        if message.author.id == self.bot.user.id:
            return
            
        # Check channel (Optional but safer) - logic based on allowing signals from ADMIN CHANNEL
        if self.admin_channel_id and message.channel.id != self.admin_channel_id:
             return

        if message.content == "!ipc_signal:ping":
            latency = round(self.bot.latency * 1000)
            await message.channel.send(f"🤖 {self.bot_name} Pong! ({latency}ms)")
            
        elif message.content == "!ipc_signal:reload":
            await message.channel.send(f"🤖 {self.bot_name}收到更新訊號，開始重載...")
            await self.do_reload(interaction=None, channel=message.channel)

    async def do_reload(self, interaction=None, channel=None):
        msg = []
        cogs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cogs')
        
        for filename in os.listdir(cogs_path):
            if filename.endswith('.py'):
                ext_name = f'cogs.{filename[:-3]}'
                try:
                    await self.bot.reload_extension(ext_name)
                    msg.append(f"✅ `{filename}` 重載成功")
                except Exception as e:
                    try:
                        await self.bot.load_extension(ext_name)
                        msg.append(f"🆕 `{filename}` 載入成功")
                    except Exception as load_err:
                        msg.append(f"❌ `{filename}` 失敗: {str(load_err)}")

        # Sync
        await self.bot.tree.sync()
        result_text = "\n".join(msg)
        
        if interaction:
            await interaction.followup.send(result_text)
        elif channel:
            await channel.send(f"🤖 {self.bot_name}重載完成！\n{result_text}")


async def setup(bot):
    await bot.add_cog(Status(bot))
