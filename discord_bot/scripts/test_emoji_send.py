
import discord
import os
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), ".env")

load_dotenv(ENV_FILE)
TOKEN = os.getenv("DISCORD_TOKEN")
CHANNEL_ID = int(os.getenv("AI_CHANNEL_ID", "0"))

class EmojiSender(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        channel = self.get_channel(CHANNEL_ID)
        if not channel:
            print(f"❌ Channel {CHANNEL_ID} not found")
        else:
            # Test Emoji: appear
            emoji_code = "<a:appear:1469966365300359229>"
            print(f"Sending {emoji_code} to {channel.name}...")
            try:
                await channel.send(f"Testing Emoji Render: {emoji_code}")
                print("✅ Sent!")
            except Exception as e:
                print(f"❌ Failed to send: {e}")
        
        await self.close()

if __name__ == "__main__":
    intents = discord.Intents.default()
    client = EmojiSender(intents=intents)
    client.run(TOKEN)
