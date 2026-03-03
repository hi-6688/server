
import discord
import os
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), ".env")

load_dotenv(ENV_FILE)
TOKEN = os.getenv("DISCORD_TOKEN")

class EmojiLister(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        print(f"Connected to {len(self.guilds)} guilds.")
        
        total_emojis = 0
        for guild in self.guilds:
            print(f"\nGuild: {guild.name} (ID: {guild.id})")
            emojis = guild.emojis
            print(f"  Count: {len(emojis)}")
            for e in emojis:
                animated_str = "a" if e.animated else ""
                print(f"  - {e.name}: <{animated_str}:{e.name}:{e.id}>")
                total_emojis += 1
        
        print(f"\nTotal Emojis Found: {total_emojis}")
        await self.close()

if __name__ == "__main__":
    intents = discord.Intents.default()
    intents.guilds = True 
    intents.emojis = True
    
    client = EmojiLister(intents=intents)
    client.run(TOKEN)
