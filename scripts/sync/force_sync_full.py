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

sys.path.append('/home/terraria/servers')

class SyncBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        cogs = ['status', 'minecraft', 'terraria', 'conch_game']
        for cog in cogs:
            try:
                print(f"Loading {cog}...")
                await self.load_extension(f'discord_bot.cogs.{cog}')
            except Exception as e:
                print(f"Error loading {cog}: {e}")

        print("Syncing guild commands globally...")
        try:
            synced = await self.tree.sync()
            print(f"Synced {len(synced)} commands: {[c.name for c in synced]}")
        except Exception as e:
            print(f"Sync error: {e}")

    async def on_ready(self):
        print(f'Logged in as {self.user} (ID: {self.user.id})')
        await self.close()

if __name__ == '__main__':
    bot = SyncBot()
    bot.run(TOKEN)
