import os
import secrets
import logging
import discord
from discord import app_commands
from dotenv import load_dotenv
from sqlmodel import Session, select
from database import engine, GameRoom

# 設定 Logging
load_dotenv()
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("DiscordBot")

# 設定 Bot Intent
intents = discord.Intents.default()
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

@client.event
async def on_ready():
    await tree.sync()
    logger.info(f'Logged in as {client.user}!')

@tree.command(name="battle", description="寶可夢對戰測試中，敬請期待")
async def battle(interaction: discord.Interaction):
    # 產生房間 ID 與 Token
    room_id = secrets.token_hex(2).upper() # e.g. "A1B2"
    host_token = secrets.token_urlsafe(16)
    
    # 寫入資料庫
    with Session(engine) as session:
        room = GameRoom(id=room_id, host_token=host_token, status="waiting")
        session.add(room)
        session.commit()
    
    # 建立私訊並發送連結
    try:
        dm_channel = await interaction.user.create_dm()
        # 假設前端是 Web 版，或是提供一個 Scheme URL 給 Godot
        link = f"請在遊戲中輸入 Token: {host_token} (Room: {room_id})"
        await dm_channel.send(f"🎮 **準備戰鬥！**\n您的房間代碼: `{room_id}`\n您的 Host Token: ||`{host_token}`||\n(請勿將 Token 給別人)")
        
        await interaction.response.send_message(f"房間已建立！請查看您的私訊 (DM)。", ephemeral=True)
    except discord.Forbidden:
        await interaction.response.send_message(f"無法傳送私訊給您，請檢查隱私設定。", ephemeral=True)

if __name__ == "__main__":
    token = os.getenv("DISCORD_TOKEN")
    if token and token != "PUT_YOUR_TOKEN_HERE":
        client.run(token)
    else:
        logger.error("No DISCORD_TOKEN found in environment variables.")
