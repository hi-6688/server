
import discord
import os
import json
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data/hihi")
EMOJI_FILE = os.path.join(DATA_DIR, "emojis.json")
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), ".env")

load_dotenv(ENV_FILE)
TOKEN = os.getenv("DISCORD_TOKEN")

class EmojiFetcher(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        
        emojis = {}
        print("Fetching emojis from all guilds...")
        
        for guild in self.guilds:
            print(f"Scanning Guild: {guild.name} ({guild.id})")
            for emoji in guild.emojis:
                print(f"  Found: {emoji.name} -> {emoji}")
                emojis[emoji.name] = str(emoji)
                
        # Save to JSON
        with open(EMOJI_FILE, 'w', encoding='utf-8') as f:
            json.dump(emojis, f, ensure_ascii=False, indent=2)
            
        print(f"✅ Saved {len(emojis)} emojis to {EMOJI_FILE}")
        await self.close()

if __name__ == "__main__":
    if not TOKEN:
        print("❌ Error: DISCORD_TOKEN not found in environment")
        exit(1)
        
    intents = discord.Intents.default()
    intents.guilds = True
    intents.emojis = True
    
    client = EmojiFetcher(intents=intents)
    client.run(TOKEN)
