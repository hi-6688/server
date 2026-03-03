
import discord
import os
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), ".env")

load_dotenv(ENV_FILE)
TOKEN = os.getenv("DISCORD_TOKEN")

class AppEmojiFetcher2(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        
        try:
            app = await self.application_info()
            print(f"App ID: {app.id}")
            
            # Using internal http client to fetch application emojis
            # GET /applications/{application.id}/emojis
            data = await self.http.request(
                discord.http.Route('GET', f'/applications/{app.id}/emojis')
            )
            
            print(f"Found {len(data['items'])} Application Emojis:")
            for e in data['items']:
                animated = e.get('animated', False)
                anim_str = "a" if animated else ""
                print(f"  - {e['name']}: <{anim_str}:{e['name']}:{e['id']}>")
                
        except Exception as e:
            print(f"❌ Error: {e}")
            
        await self.close()

if __name__ == "__main__":
    intents = discord.Intents.default()
    client = AppEmojiFetcher2(intents=intents)
    client.run(TOKEN)
