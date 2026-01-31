import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

# 載入 .env 設定 (Token)
load_dotenv()
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

    async def on_ready(self):
        print(f'🤖 機器人已登入: {self.user} (ID: {self.user.id})')
        print(f'---------------------------------------------')

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
