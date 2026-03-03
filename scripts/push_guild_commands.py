import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv('/home/terraria/servers/.env')
TOKEN = os.getenv('CONCH_TOKEN')
CHANNEL_ID = int(os.getenv('TERRARIA_CHANNEL_ID', 0))

import sys
sys.path.append('/home/terraria/servers')

class GuildSyncBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        cogs = ['status', 'minecraft', 'terraria', 'conch_game']
        for cog in cogs:
            try:
                await self.load_extension(f'discord_bot.cogs.{cog}')
                print(f"Loaded {cog}")
            except Exception as e:
                print(e)
                
    async def on_ready(self):
        print(f'Logged in as {self.user}')
        if CHANNEL_ID:
            channel = self.get_channel(CHANNEL_ID)
            if channel and channel.guild:
                guild = channel.guild
                print(f"Syncing to Guild: {guild.name} ({guild.id})")
                
                # Copy global commands to this guild
                self.tree.copy_global_to(guild=guild)
                synced = await self.tree.sync(guild=guild)
                print(f"✅ Fast Synced {len(synced)} commands to {guild.name}: {[c.name for c in synced]}")
        await self.close()

if __name__ == '__main__':
    bot = GuildSyncBot()
    bot.run(TOKEN)
