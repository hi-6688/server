import discord
import os
import asyncio
import json
import aiohttp
from discord.ext import commands
from discord import app_commands
from dotenv import load_dotenv

# 載入 .env 設定 (Token)
# 載入 .env 設定 (位於專案根目錄 servers/.env)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env'))

# 根據 BOT_MODE 選擇 Token
# CONCH = 神奇嗨螺 (功能型), HIHI = 嗨嗨 (AI 聊天型)
BOT_MODE = os.getenv('BOT_MODE', 'ALL').upper()
if BOT_MODE == 'CONCH':
    TOKEN = os.getenv('CONCH_TOKEN')
else:
    TOKEN = os.getenv('DISCORD_TOKEN')

# 設定 Intent (權限)
intents = discord.Intents.default()
intents.message_content = True # 讀取訊息權限

async def listen_to_fastapi_ws(bot):
    """(BOT_MODE=CONCH 專用) 透過 WebSocket 連接 FastAPI，即時推送開關機狀態到 Discord"""
    await bot.wait_until_ready()
    
    # 在 docker-compose.yml 內，網頁後端的 service 名稱為 web-api，但由於改用了主機網路，改用 127.0.0.1
    ws_url = "ws://127.0.0.1:24445/ws"
    
    while not bot.is_closed():
        try:
            async with aiohttp.ClientSession() as session:
                async with session.ws_connect(ws_url) as ws:
                    print(f"🔗 [Conch WebSocket] 已滿血連線至中樞 {ws_url}")
                    
                    async for msg in ws:
                        if msg.type == aiohttp.WSMsgType.TEXT:
                            try:
                                data = json.loads(msg.data)
                                if data.get("type") == "boot_progress":
                                    progress = data.get("data")
                                    message = data.get("message", "")
                                    
                                    # 抓取目前設定的發話頻道
                                    channel_id_str = os.getenv("TERRARIA_CHANNEL_ID", "0")
                                    if channel_id_str.isdigit() and int(channel_id_str) != 0:
                                        channel = bot.get_channel(int(channel_id_str))
                                        
                                        if channel:
                                            # 對應不同的狀態，機器人會在頻道大喊
                                            if progress == "vm_starting":
                                                await channel.send("⏳ **[系統同步]** 收到開機指令！正在喚醒 GCP 雲端機器...")
                                            elif progress == "agent_waiting":
                                                await channel.send("⏳ **[系統同步]** 機器已甦醒，正在等待系統內部代理連線...")
                                            elif progress == "server_starting":
                                                await channel.send("⏳ **[系統同步]** 代理已連線，正在啟動麥塊伺服器主程式...")
                                            elif progress == "online":
                                                await channel.send("✅ **[系統同步]** 伺服器啟動成功！各位可以上線囉！")
                                            elif progress == "offline" and message:
                                                await channel.send(f"❌ **[系統同步]** 啟動失敗或伺服器已關閉: `{message}`")
                            except json.JSONDecodeError:
                                pass
                        elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
                            break
        except Exception as e:
            print(f"⚠️ [Conch WebSocket] 連線異常或中斷: {e}")
            
        # 若斷線，等待 5 秒後重連
        await asyncio.sleep(5)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=commands.DefaultHelpCommand()
        )

    async def setup_hook(self):
        """啟動時自動載入 cogs 資料夾內的 extensions"""
        
        # 決定要載入哪些模組 (Split Architecture)
        mode = os.getenv('BOT_MODE', 'ALL').upper()
        
        # 定義模組清單
        cogs_map = {
            'CONCH': ['status', 'minecraft', 'terraria', 'conch_game'], # 神奇嗨螺 (功能型)
            'HIHI': ['status', 'ai_chat'],              # 嗨嗨 (靈魂型)
        }
        
        # 決定載入清單
        if mode in cogs_map:
            target_cogs = cogs_map[mode]
            print(f"🚀 [Mode: {mode}] 僅載入以下模組: {target_cogs}")
        else:
            # 預設載入所有 (ALL)
            target_cogs = [f[:-3] for f in os.listdir('./cogs') if f.endswith('.py')]
            print(f"🚀 [Mode: ALL] 載入所有模組: {target_cogs}")

        for filename in target_cogs:
            try:
                await self.load_extension(f'cogs.{filename}')
                print(f'✅ 已載入模組: {filename}')
            except Exception as e:
                print(f'❌ 無法載入模組 {filename}: {e}')
        
        # 強制同步指令 (移除舊指令，註冊新指令)
        print("🔄 正在同步全域指令到 Discord...")
        try:
            synced = await self.tree.sync()
            print(f"✅ 全域同步完成！共 {len(synced)} 個指令。")
        except Exception as e:
            print(f"❌ 指令同步失敗: {e}")

        # 註冊全域錯誤捕獲器
        async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            print(f"⚠️ 發生指令錯誤 [{interaction.command.name if interaction.command else 'Unknown'}]: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ 執行發生錯誤: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ 執行發生錯誤: {error}", ephemeral=True)
                
        self.tree.on_error = on_tree_error
        
        # 開啟神奇嗨螺專屬的中樞訂閱廣播循環
        if mode == 'CONCH':
            self.loop.create_task(listen_to_fastapi_ws(self))

    async def on_ready(self):
        print(f'🤖 機器人已登入: {self.user} (ID: {self.user.id})')
        print(f'---------------------------------------------')

        # --- 自動清理重複指令 (已停用) ---
        # 避免清除全域指令導致重新同步的延遲
        # target_channel_id = int(os.getenv('TERRARIA_CHANNEL_ID', '0'))
        # if target_channel_id:
        #     try:
        #         channel = self.get_channel(target_channel_id)
        #         if channel and channel.guild:
        #             print(f"🧹 [已略過] 正在清理伺服器 `{channel.guild.name}` 的舊指令...")
        #             # self.tree.clear_commands(guild=channel.guild)
        #             # await self.tree.sync(guild=channel.guild)
        #             # print(f"✨ 伺服器指令清理完成！(僅保留全域指令)")
        #     except Exception as e:
        #         print(f"⚠️ 清理指令時發生錯誤 (非致命): {e}")

# 啟動機器人
async def main():
    bot = MyBot()
    async with bot:
        await bot.start(TOKEN)

if __name__ == '__main__':
    if not TOKEN:
        print("❌ 錯誤: 未找到 DISCORD_TOKEN。請在 .env 檔案中設定。")
    else:
        try:
            asyncio.run(main())
        except KeyboardInterrupt:
            # allow CTRL+C to exit gracefully
            pass
