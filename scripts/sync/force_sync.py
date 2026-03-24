import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv('/home/terraria/servers/discord_bot/.env')
TOKEN = os.getenv('DISCORD_BOT_TOKEN')

class SyncBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        print("Loading minecraft cog...")
        await self.load_extension('discord_bot.cogs.minecraft')
        print("Syncing guild commands globally...")
        # Since we use app_commands without guild specific limits it should sync globally
        synced = await self.tree.sync()
        print(f"Synced {len(synced)} commands: {[c.name for c in synced]}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.close()

if __name__ == '__main__':
    # Need to append servers to path so relative imports work
    import sys
    sys.path.append('/home/terraria/servers')
    bot = SyncBot()
    bot.run(TOKEN)
