import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv
import sys

# Force unbuffered stdout
sys.stdout.reconfigure(line_buffering=True)

load_dotenv('/home/terraria/servers/.env')
TOKEN = os.getenv('CONCH_TOKEN')
CHANNEL_ID = int(os.getenv('TERRARIA_CHANNEL_ID', 0))

sys.path.append('/home/terraria/servers')

class GuildSyncBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        cogs = ['status', 'minecraft', 'terraria', 'conch_game']
        for cog in cogs:
            try:
                await self.load_extension(f'discord_bot.cogs.{cog}')
                print(f"✅ Loaded {cog}")
            except Exception as e:
                print(f"❌ Failed to load {cog}: {e}")
                
    async def on_ready(self):
        print(f'🤖 Logged in as {self.user}')
        for guild in self.guilds:
            print(f"🎯 Target Guild: {guild.name} ({guild.id})")
            try:
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"🚀 Successfully fast-synced {len(synced)} commands to {guild.name}: {[c.name for c in synced]}")
            except Exception as e:
                print(f"❌ Sync failed for {guild.name}: {e}")
            
        await self.close()

if __name__ == '__main__':
    bot = GuildSyncBot()
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Bot run error: {e}")
