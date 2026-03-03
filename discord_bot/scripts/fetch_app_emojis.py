
import discord
import os
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), ".env")

load_dotenv(ENV_FILE)
TOKEN = os.getenv("DISCORD_TOKEN")

class AppEmojiFetcher(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        
        try:
            print("Fetching Application info...")
            app = await self.application_info()
            print(f"Application: {app.name} (ID: {app.id})")
            
            print("Fetching Application Emojis...")
            emojis = await app.fetch_emojis()
            
            print(f"Found {len(emojis)} Application Emojis:")
            for e in emojis:
                animated_str = "a" if e.animated else ""
                print(f"  - {e.name}: <{animated_str}:{e.name}:{e.id}>")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            
        await self.close()

if __name__ == "__main__":
    intents = discord.Intents.default()
    client = AppEmojiFetcher(intents=intents)
    client.run(TOKEN)
