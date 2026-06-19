import sys
sys.path = [p for p in sys.path if 'honcho/src' not in p]
sys.path.insert(0, "/home/hi6688/servers/hermes-agent")
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
# CONCH = 神奇嗨螺 (功能型), HIHI = 嗨嗨 (AI 聊天型), TEST = 測試雞
BOT_MODE = os.getenv('BOT_MODE', 'ALL').upper()
if BOT_MODE == 'CONCH':
    TOKEN = os.getenv('CONCH_TOKEN')
elif BOT_MODE == 'TEST':
    TOKEN = os.getenv('TEST_TOKEN')
else:
    TOKEN = os.getenv('DISCORD_TOKEN')

# 設定 Intent (權限)
intents = discord.Intents.default()
intents.message_content = True # 讀取訊息權限

# [Deprecation] 因應 Web 管理面板與 Docker 已移除，關閉此 WebSocket 連線
# async def listen_to_fastapi_ws(bot):
#     """(BOT_MODE=CONCH 專用) 透過 WebSocket 連接 FastAPI，即時推送開關機狀態到 Discord"""
#     await bot.wait_until_ready()
#     
#     # 在 docker-compose.yml 內，網頁後端的 service 名稱為 web-api，但由於改用了主機網路，改用 127.0.0.1
#     ws_url = "ws://127.0.0.1:24445/ws"
#     
#     while not bot.is_closed():
#         try:
#             async with aiohttp.ClientSession() as session:
#                 async with session.ws_connect(ws_url) as ws:
#                     print(f"🔗 [Conch WebSocket] 已滿血連線至中樞 {ws_url}")
#                     
#                     async for msg in ws:
#                         if msg.type == aiohttp.WSMsgType.TEXT:
#                             try:
#                                 data = json.loads(msg.data)
#                                 if data.get("type") == "boot_progress":
#                                     progress = data.get("data")
#                                     message = data.get("message", "")
#                                     
#                                     # 抓取目前設定的發話頻道
#                                     channel_id_str = os.getenv("TERRARIA_CHANNEL_ID", "0")
#                                     if channel_id_str.isdigit() and int(channel_id_str) != 0:
#                                         channel = bot.get_channel(int(channel_id_str))
#                                         
#                                         if channel:
#                                             # 對應不同的狀態，機器人會在頻道大喊
#                                             if progress == "vm_starting":
#                                                 await channel.send("⏳ **[系統同步]** 收到開機指令！正在喚醒 GCP 雲端機器...")
#                                             elif progress == "agent_waiting":
#                                                 await channel.send("⏳ **[系統同步]** 機器已甦醒，正在等待系統內部代理連線...")
#                                             elif progress == "server_starting":
#                                                 await channel.send("⏳ **[系統同步]** 代理已連線，正在啟動麥塊伺服器主程式...")
#                                             elif progress == "online":
#                                                 await channel.send("✅ **[系統同步]** 伺服器啟動成功！各位可以上線囉！")
#                                             elif progress == "offline" and message:
#                                                 await channel.send(f"❌ **[系統同步]** 啟動失敗或伺服器已關閉: `{message}`")
#                             except json.JSONDecodeError:
#                                 pass
#                         elif msg.type in (aiohttp.WSMsgType.CLOSED, aiohttp.WSMsgType.ERROR):
#                             break
#         except Exception as e:
#             print(f"⚠️ [Conch WebSocket] 連線異常或中斷: {e}")
#             
#         # 若斷線，等待 5 秒後重連
#         await asyncio.sleep(5)

class MyBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix='!',
            intents=intents,
            help_command=commands.DefaultHelpCommand(),
            max_messages=50
        )

    async def setup_hook(self):
        """啟動時自動載入 cogs 資料夾內的 extensions"""
        
        # 決定要載入哪些模組 (Split Architecture)
        mode = os.getenv('BOT_MODE', 'ALL').upper()
        
        # 定義模組清單 (對應子目錄)
        cogs_map = {
            'CONCH': ['common.status', 'inactive.minecraft', 'inactive.terraria', 'conch.conch_game'], # 神奇嗨螺 (功能型)
            'HIHI': ['common.status', 'hihi.ai_chat'],              # 嗨嗨 (靈魂型)
            'TEST': ['common.status', 'inactive.vm_admin'],             # 測試機 (VM直控型)
        }
        
        # 決定載入清單
        if mode in cogs_map:
            target_cogs = cogs_map[mode]
            print(f"🚀 [Mode: {mode}] 僅載入以下模組: {target_cogs}")
        else:
            # 預設載入所有 (ALL) 但排除資源密集且暫不營運的伺服器相關模組
            excluded_cogs = ['inactive.minecraft', 'inactive.terraria', 'inactive.vm_admin']
            target_cogs = []
            for root, dirs, files in os.walk('./cogs'):
                for file in files:
                    if file.endswith('.py'):
                        # 取得相對 cogs 的路徑，如 "hihi/ai_chat.py"
                        rel_path = os.path.relpath(os.path.join(root, file), './cogs')
                        # 轉成 "hihi.ai_chat"
                        cog_name = os.path.splitext(rel_path)[0].replace(os.sep, '.')
                        if cog_name not in excluded_cogs:
                            target_cogs.append(cog_name)
            print(f"🚀 [Mode: ALL] 載入模組 (已排除 {excluded_cogs}): {target_cogs}")

        for filename in target_cogs:
            try:
                await self.load_extension(f'cogs.{filename}')
                print(f'✅ 已載入模組: {filename}')
            except Exception as e:
                print(f'❌ 無法載入模組 {filename}: {e}')
        
        # 註冊全域錯誤捕獲器
        async def on_tree_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
            print(f"⚠️ 發生指令錯誤 [{interaction.command.name if interaction.command else 'Unknown'}]: {error}")
            if not interaction.response.is_done():
                await interaction.response.send_message(f"❌ 執行發生錯誤: {error}", ephemeral=True)
            else:
                await interaction.followup.send(f"❌ 執行發生錯誤: {error}", ephemeral=True)
                
        self.tree.on_error = on_tree_error
        
        # [Deprecation] 已關閉神奇嗨螺專屬的中樞訂閱廣播循環
        # if mode == 'CONCH':
        #     self.loop.create_task(listen_to_fastapi_ws(self))

    async def on_ready(self):
        print(f'🤖 機器人已登入: {self.user} (ID: {self.user.id})')
        print(f'---------------------------------------------')

        # 1. 先做區域同步 (此時全域指令樹還有內容可複製)
        for guild in self.guilds:
            try:
                print(f"📋 正在同步指令到伺服器 `{guild.name}`...")
                self.tree.copy_global_to(guild=guild)
                synced_guild = await self.tree.sync(guild=guild)
                print(f"✨ 區域指令同步完成！共 {len(synced_guild)} 個！")
            except Exception as e:
                print(f"⚠️ 區域伺服器 {guild.name} 指令同步發生錯誤: {e}")

        # 2. 清除全域指令 (避免與區域指令重複)
        try:
            self.tree.clear_commands(guild=None)
            await self.tree.sync()
            print("🧹 全域指令已清除 (僅保留區域指令)")
        except Exception as e:
            print(f"⚠️ 清除全域指令失敗: {e}")

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
