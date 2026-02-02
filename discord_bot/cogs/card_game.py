import discord
from discord import app_commands
from discord.ext import commands
from sqlmodel import Field, SQLModel, create_engine, Session
from typing import Optional
import secrets
import os

# Define the Model (Same as in CardGame_Project/backend/database.py)
class GameRoom(SQLModel, table=True):
    id: str = Field(primary_key=True)
    host_token: str
    guest_token: Optional[str] = None
    status: str = "waiting"

# Connect to the existing SQLite database in the CardGame folder
# Note: This path assumes the bot is run from ~/servers root
DB_PATH = "sqlite:///CardGame_Project/backend/dev.db"
engine = create_engine(DB_PATH)

class CardGameCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="battle", description="開啟卡牌對戰房間 (Pokemon TCG Style)")
    async def battle(self, interaction: discord.Interaction):
        # 1. Generate Room ID and Token
        room_id = secrets.token_hex(2).upper() # e.g. "A1B2"
        host_token = secrets.token_urlsafe(16)

        # 2. Save to Database
        try:
            with Session(engine) as session:
                room = GameRoom(id=room_id, host_token=host_token, status="waiting")
                session.add(room)
                session.commit()
        except Exception as e:
            await interaction.response.send_message(f"❌ 資料庫錯誤: {e}", ephemeral=True)
            return

        # 3. Send DM to User
        try:
            dm_channel = await interaction.user.create_dm()
            await dm_channel.send(
                f"🎮 **準備戰鬥！**\n"
                f"您的房間代碼: `{room_id}`\n"
                f"您的 Host Token: ||`{host_token}`||\n"
                f"(請在遊戲中輸入此 Token 以主持遊戲)"
            )
            await interaction.response.send_message(f"✅ 房間已建立！請查看您的私訊 (DM)。", ephemeral=True)
        except discord.Forbidden:
            await interaction.response.send_message(f"❌ 無法傳送私訊給您，請檢查隱私設定。", ephemeral=True)

async def setup(bot: commands.Bot):
    await bot.add_cog(CardGameCog(bot))
