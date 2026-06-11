import discord
from discord.ext import commands
from discord import app_commands
import os
import aiohttp
import asyncio
from dotenv import load_dotenv
from utils.gcp_manager import GCPManager

load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), '.env'))

class VMAdmin(commands.Cog):
    """測試機專屬：VM2 直控管理模組 (Administrator 限定)"""

    def __init__(self, bot):
        self.bot = bot
        # VM2 的 GCP 專案與區域設定
        self.gcp_project = "project-ad2eecb1-dd0f-4cf4-b1a"
        self.gcp_zone = "asia-east1-c"
        self.vm_name = "instance-20260220-174959"
        self.gcp_manager = GCPManager(project_id=self.gcp_project, zone=self.gcp_zone)
        
        # VM2 內部代理程式的連線資訊
        self.agent_port = 9999
        self.agent_secret = "hihi_secret_key_2026"

    async def _agent_post(self, vm_ip: str, action: str, timeout: int = 5, **kwargs) -> dict:
        """向 VM2 內部代理程式發送 HTTP POST 請求"""
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
            return {"status": "error", "message": str(e)}

    @app_commands.command(name="vm開機", description="[免自動關機] 強制啟動 VM2")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_vm_start(self, interaction: discord.Interaction):
        # 先用 defer 佔住回應位 (避免 3 秒逾時)
        await interaction.response.defer(ephemeral=False)
        
        # 1. 啟動 VM (同步阻塞呼叫，丟到背景執行緒)
        await interaction.followup.send("⚙️ **[後台管理]** 正在向 GCP 發送開機請求...")
        success = await asyncio.to_thread(self.gcp_manager.start_instance, self.vm_name)
        if not success:
            await interaction.followup.send("❌ 開機請求失敗，請檢查 GCP 權限或狀態。")
            return
            
        await interaction.followup.send("✅ GCP 虛擬機正在啟動！等待代理程式上線以鎖定自動關機...")

        # 2. 等待 VM 啟動並獲取 IP
        await asyncio.sleep(5) 
        vm_ip = None
        for _ in range(30): # 最多等 60 秒
            vm_ip = await asyncio.to_thread(self.gcp_manager.get_instance_ip, self.vm_name)
            if vm_ip:
                break
            await asyncio.sleep(2)
            
        if not vm_ip:
            await interaction.followup.send("⚠️ 無法獲取 VM2 的內部 IP，自動關機可能未被鎖定，請手動留意！")
            return

        # 3. 嘗試連線 Agent 並發送 disable_auto_shutdown
        agent_ready = False
        for _ in range(15): # 試 30 秒
            res = await self._agent_post(vm_ip, "disable_auto_shutdown", timeout=2)
            if res.get("status") == "success":
                agent_ready = True
                break
            await asyncio.sleep(2)
            
        if agent_ready:
            await interaction.followup.send("🔒 **[鎖定成功]** 已強制關閉 VM2 的 10 分鐘自動休眠功能！\n🌍 伺服器啟動中，稍後可查閱 `/vm狀態`")
        else:
            await interaction.followup.send("⚠️ 雖然 VM 開機了，但無法連線至 VM2 代理程式，**自動休眠鎖定失敗！** 請注意 10 分鐘後伺服器可能會自動斷電。")

    @app_commands.command(name="vm關機", description="安全存檔並強制關閉 VM2")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_vm_stop(self, interaction: discord.Interaction):
        # 先用 defer 佔住回應位
        await interaction.response.defer(ephemeral=False)
        
        await interaction.followup.send("🔴 **[後台管理]** 準備安全關閉 VM2...")
        
        vm_ip = await asyncio.to_thread(self.gcp_manager.get_instance_ip, self.vm_name)
        if vm_ip:
            # 嘗試通知內部 Minecraft 存檔
            await interaction.followup.send("⏳ 正在通知所有內建層 (Screen) 執行安全存檔 (stop)...")
            res = await self._agent_post(vm_ip, "get_system_status")
            screens = res.get("screens", [])
            for s in screens:
                await self._agent_post(vm_ip, "execute_command", screen_name=s, command="say 後台管理員已下達關機指令，開始安全存檔...\r")
                await asyncio.sleep(1)
                await self._agent_post(vm_ip, "execute_command", screen_name=s, command="stop\r")
            
            if screens:
                await asyncio.sleep(5) # 等待 5 秒讓遊戲存檔
        
        # 強制從 GCP 斷電 (同步阻塞呼叫)
        success = await asyncio.to_thread(self.gcp_manager.stop_instance, self.vm_name)
        if success:
            await interaction.followup.send("⚡ GCP 已受理斷電請求，伺服器將在幾秒內離線。")
        else:
            await interaction.followup.send("❌ GCP 斷電請求失敗，請手動登入 GCP 檢查！")

    @app_commands.command(name="vm狀態", description="查詢 VM2 底層狀態")
    @app_commands.checks.has_permissions(administrator=True)
    async def slash_vm_status(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=False)
        
        # 同步阻塞呼叫丟到背景執行緒
        status = await asyncio.to_thread(self.gcp_manager.get_instance_status, self.vm_name)
        if not status:
             status = "UNKNOWN_OR_ERROR"

        msg = f"🖥️ **VM2 主機狀態**: `{status}`\n"
        
        if status == "RUNNING":
            ip = await asyncio.to_thread(self.gcp_manager.get_instance_ip, self.vm_name)
            public_ip = await asyncio.to_thread(self.gcp_manager.get_instance_public_ip, self.vm_name)
            msg += f"🌐 內部 IP: `{ip}`\n🌍 外部 IP: `{public_ip}`\n"
            
            # 連線 Agent 抓取進階資訊
            res = await self._agent_post(ip, "get_system_status", timeout=2)
            if res.get('status') == 'success':
                screens = res.get('screens', [])
                msg += f"🔌 代理程式: 🟢 連線正常\n🏃 運作中的子畫面: `{', '.join(screens) if screens else '無'}`"
                # 再檢查鎖定狀態
                sys_res = await self._agent_post(ip, "get_agent_info", timeout=2)
                if sys_res.get('status') == 'success':
                    lock_state = sys_res.get("auto_shutdown_enabled", "未知")
                    msg += f"\n🔒 防休眠保護: `{'已上鎖 (防休眠)' if not lock_state else '未保護 (10m)'}`"
            else:
                msg += f"🔌 代理程式: 🔴 無法連線 (可能剛開機或代理已崩潰)"
        
        await interaction.followup.send(msg)

async def setup(bot):
    await bot.add_cog(VMAdmin(bot))
