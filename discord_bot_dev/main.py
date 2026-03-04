import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# 載入 .env 設定 (Token)
# 載入 .env 設定 (位於專案根目錄 servers/.env)
# 載入 .env 設定 (優先讀取當前目錄)
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
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
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f'✅ 已載入模組: {filename}')
                except Exception as e:
                    print(f'❌ 無法載入模組 {filename}: {e}')
        
        # 強制同步指令 (移除舊指令，註冊新指令)
        print("🔄 正在同步指令到 Discord...")
        try:
            synced = await self.tree.sync()
            print(f"✅ 同步完成！共 {len(synced)} 個指令。")
        except Exception as e:
            print(f"❌ 指令同步失敗: {e}")

    async def on_ready(self):
        print(f'🤖 機器人已登入: {self.user} (ID: {self.user.id})')
        print(f'---------------------------------------------')

        # --- 自動清理重複指令 (針對當前伺服器) ---
        target_channel_id = int(os.getenv('TERRARIA_CHANNEL_ID', '0'))
        if target_channel_id:
            try:
                channel = self.get_channel(target_channel_id)
                if channel and channel.guild:
                    print(f"🧹 正在清理伺服器 `{channel.guild.name}` 的舊指令...")
                    self.tree.clear_commands(guild=channel.guild)
                    await self.tree.sync(guild=channel.guild)
                    print(f"✨ 伺服器指令清理完成！(僅保留全域指令)")
            except Exception as e:
                print(f"⚠️ 清理指令時發生錯誤 (非致命): {e}")

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
