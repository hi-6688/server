
import discord
import os
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), ".env")

load_dotenv(ENV_FILE)
TOKEN = os.getenv("DISCORD_TOKEN")
TARGET_GUILD_ID = 1225815281100914699
TARGET_EMOJI_ID = 1469966365300359229

class EmojiDebugger(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        
        guild = self.get_guild(TARGET_GUILD_ID)
        if not guild:
            print(f"❌ Could not find guild {TARGET_GUILD_ID} in cache")
            # Try fetching
            try:
                guild = await self.fetch_guild(TARGET_GUILD_ID)
                print(f"✅ Fetched guild: {guild.name}")
            except Exception as e:
                print(f"❌ Failed to fetch guild: {e}")
                await self.close()
                return

        print(f"Guild Emojis Count (Cache): {len(guild.emojis)}")
        
        try:
            print(f"Attempting to fetch emoji {TARGET_EMOJI_ID}...")
            emoji = await guild.fetch_emoji(TARGET_EMOJI_ID)
            print(f"✅ FOUND EMOJI:")
            print(f"  Name: {emoji.name}")
            print(f"  ID: {emoji.id}")
            print(f"  String: {emoji}")
        except Exception as e:
            print(f"❌ Failed to fetch emoji: {e}")
            
        await self.close()

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.guilds = True
    intents.emojis = True # Privileged intent?
    
    client = EmojiDebugger(intents=intents)
    client.run(TOKEN)
