import discord
from discord.ext import commands

class Status(commands.Cog):
    """基本狀態指令"""

    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        # 當這個模組載入完成時觸發
        print(f'⚙️ Status 模組已準備就緒')

    @commands.command(name="ping")
    async def ping(self, ctx):
        """測試機器人延遲"""
        latency = round(self.bot.latency * 1000)
        await ctx.send(f'🏓 Pong! 延遲: {latency}ms')

    @commands.command(name="hello")
    async def hello(self, ctx):
        """打招呼"""
        await ctx.send(f'你好 {ctx.author.mention}！我是一個模組化的機器人。')

async def setup(bot):
    await bot.add_cog(Status(bot))
