import discord
import os
import asyncio
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# 載入 .env 設定 (Token)
# 載入 .env 設定 (位於專案根目錄 servers/.env)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# 根據 BOT_MODE 選擇 Token
# CONCH = 神奇嗨螺 (功能型), HIHI = 嗨嗨 (AI 聊天型)
BOT_MODE = os.getenv('BOT_MODE', 'ALL').upper()
if BOT_MODE == 'CONCH':
    TOKEN = os.getenv('CONCH_TOKEN')
else:
    TOKEN = os.getenv('DISCORD_TOKEN')

# 設定 Intent (權限)
intents = discord.Intents.default()
intents.message_content = True # 讀取訊息權限

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )

    async def setup_hook(self):
        """啟動時自動載入 cogs 資料夾內的 extensions"""
        
        # 決定要載入哪些模組 (Split Architecture)
        mode = os.getenv('BOT_MODE', 'ALL').upper()
        
        # 定義模組清單
        cogs_map = {
            'CONCH': ['status', 'minecraft', 'terraria', 'conch_game'], # 神奇嗨螺 (功能型)
            'HIHI': ['status', 'ai_chat'],              # 嗨嗨 (靈魂型)
        }
        
        # 決定載入清單
        if mode in cogs_map:
            target_cogs = cogs_map[mode]
            print(f"🚀 [Mode: {mode}] 僅載入以下模組: {target_cogs}")
        else:
            # 預設載入所有 (ALL)
            target_cogs = [f[:-3] for f in os.listdir('./cogs') if f.endswith('.py')]
            print(f"🚀 [Mode: ALL] 載入所有模組: {target_cogs}")

        for filename in target_cogs:
            try:
                await self.load_extension(f'cogs.{filename}')
                print(f'✅ 已載入模組: {filename}')
            except Exception as e:
                print(f'❌ 無法載入模組 {filename}: {e}')
        
        # 強制同步指令 (移除舊指令，註冊新指令)
        print("🔄 正在同步全域指令到 Discord...")
        try:
            synced = await self.tree.sync()
            print(f"✅ 全域同步完成！共 {len(synced)} 個指令。")
        except Exception as e:
            print(f"❌ 指令同步失敗: {e}")

        # 註冊全域錯誤捕獲器
        async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            print(f"⚠️ 發生指令錯誤 [{interaction.command.name if interaction.command else 'Unknown'}]: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ 執行發生錯誤: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ 執行發生錯誤: {error}", ephemeral=True)
                
        self.tree.on_error = on_tree_error

    async def on_ready(self):
        print(f'🤖 機器人已登入: {self.user} (ID: {self.user.id})')
        print(f'---------------------------------------------')

        # --- 自動清理重複指令 (已停用) ---
        # 避免清除全域指令導致重新同步的延遲
        # target_channel_id = int(os.getenv('TERRARIA_CHANNEL_ID', '0'))
        # if target_channel_id:
        #     try:
        #         channel = self.get_channel(target_channel_id)
        #         if channel and channel.guild:
        #             print(f"🧹 [已略過] 正在清理伺服器 `{channel.guild.name}` 的舊指令...")
        #             # self.tree.clear_commands(guild=channel.guild)
        #             # await self.tree.sync(guild=channel.guild)
        #             # print(f"✨ 伺服器指令清理完成！(僅保留全域指令)")
        #     except Exception as e:
        #         print(f"⚠️ 清理指令時發生錯誤 (非致命): {e}")

# 啟動機器人
async def main():
    bot = MyBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    if not TOKEN:
        print("❌ 錯誤: 未找到 DISCORD_TOKEN。請在 .env 檔案中設定。")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            # allow CTRL+C to exit gracefully
            pass
