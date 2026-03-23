import discord
from discord.ext import commands, tasks
from discord import app_commands
import asyncio
import os
import re
import datetime
import json
import logging
from dotenv import load_dotenv
from discord_bot.utils.gcp_manager import GCPManager
import aiohttp

logger = logging.getLogger('hihi_bot')

# Load .env (from project root)
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

# Paths
INSTANCES_FILE = "/home/terraria/servers/web_interface/instances.json"
MC_DEBUG_FILE = "/home/terraria/servers/mc_debug.log"

# Regex Patterns
import aiohttp

# ... (Regex Patterns)
JOIN_PATTERN = re.compile(r'\[PlayerJoin\] (.+)')
LEFT_PATTERN = re.compile(r'\[PlayerLeave\] (.+)')
LIST_PATTERN = re.compile(r'(?:There are|共有)\s+(\d+)/(\d+)\s+(?:players online|玩家在線上)')
CHAT_PATTERN = re.compile(r'\[ChatLog\]\s+<(.+?)>\s+(.*)')

class JoinButton(discord.ui.View):
    def __init__(self, ip, port, server_name):
        super().__init__(timeout=None)
        self.ip = ip
        self.port = port
        self.server_name = server_name

    @discord.ui.button(label="加入伺服器", style=discord.ButtonStyle.success, emoji="🚀")
    async def join(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Create minecraft:// link
        link = f"minecraft://{self.ip}:{self.port}"
        
        embed = discord.Embed(title=f"🌍 加入 {self.server_name}", color=0x00ff00)
        embed.add_field(name="IP 位址", value=f"`{self.ip}`", inline=True)
        embed.add_field(name="通訊埠 (Port)", value=f"`{self.port}`", inline=True)
        embed.description = f"點擊連結加入 (如果已安裝 Minecraft Bedrock)：\n**[{link}]({link})**\n\n或手動新增伺服器。"
        
        await interaction.response.send_message(embed=embed, ephemeral=True)

class Minecraft(commands.Cog):
    """Minecraft Bedrock 遠端多服管理模組"""

    def __init__(self, bot):
        self.bot = bot
        self.instances = [] # List of dicts
        self.channel_map = {} # channel_id -> [instance_uuid, ...]
        self.log_tasks = {} # uuid -> task
        self.player_counts = {} # uuid -> count
        self.last_instances_mtime = 0
        self.public_ip = "127.0.0.1" # Default, updated in on_ready (for VM1)
        self.vm2_ip = None # IP cache for VM2
        
        # Load GCP Settings from env (or hardcode for now based on our migration)
        # We will use the ones configured in our tests
        self.gcp_project = "project-ad2eecb1-dd0f-4cf4-b1a"
        self.gcp_zone = "asia-east1-c"
        self.gcp_manager = GCPManager(project_id=self.gcp_project, zone=self.gcp_zone)
        
        # Agent API Settings
        self.agent_port = 9999
        self.agent_secret = "hihi_secret_key_2026"

    def log_debug(self, msg):
        try:
            with open(MC_DEBUG_FILE, "a", encoding='utf-8') as f:
                f.write(f"{datetime.datetime.now()} [DEBUG] {msg}\n")
        except:
            print(f"[Fallback Print] {msg}")

    def load_instances(self):
        """讀取 instances.json 並更新狀態"""
        self.instances = []
        self.channel_map = {}
        
        if not os.path.exists(INSTANCES_FILE):
            self.log_debug(f"❌ 無法找到實例設定檔: {INSTANCES_FILE}")
            return

        try:
            with open(INSTANCES_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.instances = data.get('instances', [])
        except Exception as e:
            self.log_debug(f"❌ 讀取實例設定失敗: {e}")
            return

        # Build Maps
        for inst in self.instances:
            cid = inst.get('discord_channel_id')
            if cid:
                try:
                    cid_int = int(cid)
                    if cid_int not in self.channel_map:
                        self.channel_map[cid_int] = []
                    self.channel_map[cid_int].append(inst)
                except:
                    pass
            
            # Init player count
            if inst['uuid'] not in self.player_counts:
                self.player_counts[inst['uuid']] = 0

        print(f"✅ Loaded {len(self.instances)} instances. Channel Map: {list(self.channel_map.keys())}")

    async def cleanup_tasks(self):
        """取消所有監控任務"""
        for uuid, task in self.log_tasks.items():
            task.cancel()
        self.log_tasks = {}

    async def start_monitors(self):
        """為每個實例啟動 Log 監控 (這部分在遠端架構中，如果需要即時 log，需要 Agent API 提供 WebSocket 或是 polling)
        因為改成遠端，原先的 'tail -f' 做法無法直接跨機器使用。
        目前可以保留每分鐘 Sync 玩家人數的輪詢 (在 status_loop 中做)。
        暫停本機的 log 檔案監聽。
        """
        await self.cleanup_tasks()
        print("   [Info] Local log monitoring is disabled in remote Architecture. Syncing handled via status_loop polling.")

    @commands.Cog.listener()
    async def on_ready(self):
        print(f'🧱 Minecraft 多服模組載入中...')
        
        # Fetch Public IP
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get('https://api.ipify.org') as resp:
                    if resp.status == 200:
                        self.public_ip = await resp.text()
                        print(f"🌍 Detected Public IP: {self.public_ip}")
        except Exception as e:
            print(f"⚠️ Failed to fetch public IP: {e}")
            
        self.load_instances()
        await self.start_monitors()
        
        if not self.status_loop.is_running():
            self.status_loop.start()

    async def cog_unload(self):
        await self.cleanup_tasks()
        if self.status_loop.is_running():
            self.status_loop.cancel()

    @app_commands.command(name="mc重載", description="重新載入 Minecraft 實例設定")
    @app_commands.checks.has_permissions(administrator=True)
    async def reload_config(self, interaction: discord.Interaction):
        """重新讀取伺服器列表並重啟監控"""
        await interaction.response.send_message("🔄 正在重新載入 Minecraft 實例設定...", ephemeral=True)
        self.load_instances()
        await self.start_monitors()
        await interaction.followup.send(f"✅ 載入完成！共 {len(self.instances)} 個實例。", ephemeral=True)

    @commands.Cog.listener()
    async def on_message(self, message):
        if message.author.bot:
            return
            
        # Check if this channel is mapped to any instance
        if message.channel.id in self.channel_map:
            targets = self.channel_map[message.channel.id]
            clean_msg = message.content.replace('"', '\\"')
            cmd_text = f'say <{message.author.display_name}> {clean_msg}'
            
            count = 0
            for inst in targets:
                await self.send_command_to_instance(inst, cmd_text)
                count += 1
            
            # self.log_debug(f"Forwarded message to {count} instances.")

    async def _agent_post(self, vm_ip: str, action: str, timeout: int = 5, **kwargs) -> dict:
        """Helper to send requests to Agent API"""
        if not vm_ip:
            return {"status": "error", "message": "No IP provided"}
            
        url = f"http://{vm_ip}:{self.agent_port}/"
        headers = {"Authorization": f"Bearer {self.agent_secret}", "Content-Type": "application/json"}
        payload = {"action": action, **kwargs}
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(url, headers=headers, json=payload, timeout=timeout) as resp:
                    resp.raise_for_status()
                    return await resp.json()
        except Exception as e:
            self.log_debug(f"Agent POST failed to {vm_ip} for {action}: {e}")
            return {"status": "error", "message": str(e)}

    async def send_command_to_instance(self, instance, cmd):
        """Inject command via remote Agent API"""
        screen_name = instance.get('screen_name')
        vm_name = instance.get('vm_name', 'instance-20260220-174959') # default to our VM2
        
        if not screen_name: return

        # 1. We need the VM's internal or external IP. Since they are in the same network,
        # we can just use the internal IP if we know it, or fetch it via gcloud.
        # For simplicity, we fetch it dynamically or just try to talk to it.
        # In a real setup, instance configuration should store the VM's internal IP.
        vm_ip = self.gcp_manager.get_instance_ip(vm_name)
        if not vm_ip:
            self.log_debug(f"Cannot find IP for VM {vm_name}")
            return

        res = await self._agent_post(vm_ip, "execute_command", screen_name=screen_name, command=cmd)
        if res.get('status') != 'success':
            self.log_debug(f"❌ Failed to send to {instance['name']} via agent: {res}")
            
    @app_commands.command(name="mc開機", description="啟動 Minecraft 遠端雲端主機")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_mc_start(self, interaction: discord.Interaction):
        await interaction.response.send_message("⚙️ 正在向 Google 機房發送通電啟動指令，請稍候約 10 秒...", ephemeral=False)
        
        # Hardcoded for now based on migration plan
        vm_name = "instance-20260220-174959"
        
        success = self.gcp_manager.start_instance(vm_name)
        if success:
            await asyncio.sleep(5) # wait a bit for IP to populate
            ip = self.gcp_manager.get_instance_ip(vm_name)
            public_ip = self.gcp_manager.get_instance_public_ip(vm_name)
            self.vm2_ip = ip # Update VM2 IP cache

            # 從網頁介面載入代理工具並觸發離線同步
            try:
                import sys
                import os
                api_path = "/home/terraria/servers/web_interface"
                if api_path not in sys.path: sys.path.append(api_path)
                import proxy_helpers
                proxy_helpers.flush_offline_cache()
            except Exception as e:
                self.log_debug(f"Failed to flush offline cache: {e}")
            
            embed = discord.Embed(title="🟢 遊戲伺服器已開機通電", color=0x00FF00)
            embed.description = "**伺服器連線資訊:**"
            embed.add_field(name="🌍 最新浮動 IP", value=f"`{public_ip}`", inline=False)
            embed.add_field(name="⚠️ 提醒", value="目前 IP 為動態分配，請玩家於遊戲選單中更新此最新 IP 加入遊戲。", inline=False)
            await interaction.followup.send(embed=embed)
        else:
            await interaction.followup.send("❌ 啟動失敗，請檢查 GCP 設定。")
            
    @app_commands.command(name="mc關機", description="關閉 Minecraft 遠端雲端主機 (省錢)")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_mc_stop(self, interaction: discord.Interaction):
        await interaction.response.send_message("🔴 伺服器正在執行安全存檔，完成後大約一分鐘內將自動切斷雲端主機電源。", ephemeral=False)
        
        # 關機前標記狀態，等待 VM2 透過 Webhook 回傳「Quit correctly」事件時切斷電源
        try:
            pending_file = '/home/terraria/servers/web_interface/.pending_vm_shutdown'
            with open(pending_file, 'w') as f:
                f.write('manual_discord')
        except Exception as e:
            self.log_debug(f"Failed to set pending shutdown flag: {e}")

        # 發送停止指令給所有 Minecraft 螢幕
        for inst in self.instances:
            await self.send_command_to_instance(inst, "say Discord 機器人發起安全關機指令，系統執行存檔並準備斷電...\r")
            await asyncio.sleep(1)
            await self.send_command_to_instance(inst, "stop\r")

    async def read_log_loop(self, uuid, log_file):
        """Old local tail logic removed. Real-time log scraping is suspended in remote v1."""
        pass

    async def parse_line(self, uuid, line):
        """Old local parsing logic kept for reference but unused in pure polling."""
        pass

    @tasks.loop(minutes=2)
    async def status_loop(self):
        # 1. Check if instances.json changed
        try:
            if os.path.exists(INSTANCES_FILE):
                mtime = os.path.getmtime(INSTANCES_FILE)
                if self.last_instances_mtime == 0:
                     self.last_instances_mtime = mtime
                elif mtime > self.last_instances_mtime:
                    print(f"🔄 Detected instances.json change (mtime: {mtime}), reloading...")
                    self.load_instances()
                    await self.start_monitors()
                    self.last_instances_mtime = mtime
        except Exception as e:
            print(f"❌ Error checking instances file: {e}")

        # 2. 移除無效的玩家人數定期輪詢，改為 On-Demand (指令觸發時才抓)

    @app_commands.command(name="mc狀態", description="查看所有 Minecraft 伺服器狀態")
    async def slash_mc_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        vm_name = "instance-20260220-174959" # default VM2
        vm_ip = self.vm2_ip
        
        # 1. 快速通訊測試 (跳過慢速的 GCP 查詢)，設定 1 秒 Timeout 預防死聯
        res = await self._agent_post(vm_ip, "get_system_status", timeout=1.5)
        
        # 如果無法連線，才去問 GCP 是不是關機了或換 IP 了
        if res.get('status') != 'success':
            status = self.gcp_manager.get_instance_status(vm_name)
            if status != "RUNNING":
                msg = f"🔴 **主機未開機** (狀態: {status})\n若要遊玩請先使用 `/mc開機`"
                await interaction.followup.send(msg)
                return
            
            # 如果有通電但連不上，可能是換 IP 了，重新抓取一次
            vm_ip = self.gcp_manager.get_instance_ip(vm_name)
            self.vm2_ip = vm_ip # 更新快取
            res = await self._agent_post(vm_ip, "get_system_status", timeout=2)
            
            if res.get('status') != 'success':
                await interaction.followup.send(f"⚠️ 主機已開機 ({vm_ip})，但遊戲引擎尚未就緒或啟動中...\n*(Agent API 無法連線)*")
                return

        active_screens = res.get('screens', [])
        
        embed = discord.Embed(title="🧱 Minecraft 多重伺服器狀態", color=0x00FF00)
        public_ip = self.gcp_manager.get_instance_public_ip(vm_name) or "嘗試獲取中..."
        embed.description = f"🌍 主機 IP: `{public_ip}`\n"
        
        # 4. 針對每一個實例抓取詳細資料 (嘗試併發執行以節省時間)
        async def fetch_instance_status(inst):
            screen_name = inst.get('screen_name')
            if screen_name in active_screens:
                # 在線！嘗試抓玩家數量
                await self._agent_post(vm_ip, "execute_command", screen_name=screen_name, command="list")
                await asyncio.sleep(0.3) # 縮短等待時間
                
                log_path = f"{inst['path']}/bedrock_screen.log"
                log_res = await self._agent_post(vm_ip, "read_log_tail", filepath=log_path, lines=15)
                
                player_display = "? 人"
                if log_res.get('status') == 'success':
                    content = log_res.get('content', '')
                    matches = LIST_PATTERN.findall(content)
                    if matches:
                        player_display = f"{matches[-1][0]} / {matches[-1][1]} 人"
                        
                return {"name": inst['name'], "port": inst['port'], "status": "online", "players": player_display}
            else:
                return {"name": inst['name'], "port": inst['port'], "status": "offline", "players": "N/A"}

        # 啟動併發任務
        tasks = [fetch_instance_status(inst) for inst in self.instances]
        results = await asyncio.gather(*tasks)

        for r in results:
            if r["status"] == "online":
                embed.add_field(name=f"🟢 {r['name']}", value=f"Port: `{r['port']}`\n玩家: {r['players']}", inline=False)
            else:
                embed.add_field(name=f"🔴 {r['name']}", value=f"Port: `{r['port']}`\n狀態: 伺服器未運行", inline=False)
                
        await interaction.followup.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Minecraft(bot))
