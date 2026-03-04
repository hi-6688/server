import discord
from discord import app_commands
from discord.ext import commands
import os
from dotenv import load_dotenv

# Load Command Config
import json
CMD_CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'commands.json')
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
        
        # Load Admin Channel ID
        admin_channel_str = FULL_CONFIG.get('channels', {}).get('後台管理頻道', '0')
        self.admin_channel_id = int(admin_channel_str) if admin_channel_str else 0

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'⚙️ Status 模組已準備就緒 (Log Channel: {self.log_channel_id})')
        self.log_channel = self.bot.get_channel(self.log_channel_id)
        if self.log_channel:
            # 發送啟動訊息
            embed = discord.Embed(title="🤖 機器人已重啟", description="設定檔已重新載入！指令列表已更新。", color=0x00ff00)
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

    @app_commands.command(
        name=CMD_CONFIG.get('ping', {}).get('name', 'ping'),
        description=CMD_CONFIG.get('ping', {}).get('description', 'Ping bot')
    )
    async def slash_ping(self, interaction: discord.Interaction):
        # Debug Log
        print(f"[DEBUG] Ping cmd from Channel: {interaction.channel_id}")

        if not await self.verify_permission(interaction, 'ping'):
             return

        latency = round(self.bot.latency * 1000)
        await interaction.response.send_message(f'🏓 測試機 Pong! 延遲: {latency}ms\n📡 正在呼叫神奇嗨螺...')
        
        # IPC Signal
        if self.admin_channel_id:
            admin_channel = self.bot.get_channel(self.admin_channel_id)
            if admin_channel:
                await admin_channel.send(f"!ipc_signal:ping")

    @app_commands.command(
        name=CMD_CONFIG.get('reload', {}).get('name', 'reload'),
        description=CMD_CONFIG.get('reload', {}).get('description', 'Reload modules')
    )
    async def slash_reload(self, interaction: discord.Interaction):
        if not await self.verify_permission(interaction, 'reload'):
             return

        await interaction.response.defer(ephemeral=False)
        
        msg = []
        # 重新掃描 cogs 資料夾
        cogs_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'cogs')
        
        for filename in os.listdir(cogs_path):
            if filename.endswith('.py'):
                ext_name = f'cogs.{filename[:-3]}'
                try:
                    await self.bot.reload_extension(ext_name)
                    msg.append(f"✅ `{filename}` 重載成功")
                except Exception as e:
                    # 如果是還沒載入的（例如新檔案），嘗試 load
                    try:
                        await self.bot.load_extension(ext_name)
                        msg.append(f"🆕 `{filename}` 載入成功")
                    except Exception as load_err:
                        msg.append(f"❌ `{filename}` 失敗: {str(load_err)}")

        # 同步指令到 Discord
        # 同步指令到 Discord (全域同步)
        # 同步指令到 Discord
        await self.bot.tree.sync()
        
        msg.append("📡正在廣播同步訊號...")
        await interaction.followup.send("\n".join(msg))
        
        # IPC Signal
        if self.admin_channel_id:
            admin_channel = self.bot.get_channel(self.admin_channel_id)
            if admin_channel:
                await admin_channel.send(f"!ipc_signal:reload")

async def setup(bot):
    await bot.add_cog(Status(bot))
