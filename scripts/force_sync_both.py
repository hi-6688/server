import asyncio
import os
import discord
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv('/home/terraria/servers/.env')
TOKEN_HIHI = os.getenv('DISCORD_TOKEN')
TOKEN_CONCH = os.getenv('CONCH_TOKEN')

import sys
sys.path.append('/home/terraria/servers')

class ClearBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        print("[HiHi] Clearing global commands...")
        self.tree.clear_commands(guild=None)
        synced = await self.tree.sync()
        print(f"[HiHi] Synced {len(synced)} commands.")

    async def on_ready(self):
        print(f'[HiHi] Logged in as {self.user} (ID: {self.user.id})')
        await self.close()

class SyncConchBot(commands.Bot):
    def __init__(self):
        super().__init__(command_prefix="!", intents=discord.Intents.default())

    async def setup_hook(self):
        print("[Conch] Loading minecraft cog...")
        await self.load_extension('discord_bot.cogs.minecraft')
        print("[Conch] Syncing guild commands globally...")
        synced = await self.tree.sync()
        print(f"[Conch] Synced {len(synced)} commands: {[c.name for c in synced]}")

    async def on_ready(self):
        print(f'[Conch] Logged in as {self.user} (ID: {self.user.id})')
        await self.close()

async def main():
    if TOKEN_HIHI:
        print("--- Running HiHi Clear ---")
        hihi_bot = ClearBot()
        await hihi_bot.start(TOKEN_HIHI)
    
    if TOKEN_CONCH:
        print("--- Running Conch Sync ---")
        conch_bot = SyncConchBot()
        await conch_bot.start(TOKEN_CONCH)

if __name__ == '__main__':
    asyncio.run(main())
