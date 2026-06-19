import json
import urllib.request
import urllib.error

BDS_VERSIONS_URL = "https://raw.githubusercontent.com/Bedrock-OSS/BDS-Versions/main/versions.json"

def get_latest_bds_info(platform="linux", channel="stable"):
    """
    獲取最新 Bedrock Dedicated Server 的版本號與下載連結。
    :param platform: 'linux' 或 'windows'
    :param channel: 'stable' 或 'preview'
    :return: dict 包含 'version' 與 'download_url'
    """
    try:
        req = urllib.request.Request(BDS_VERSIONS_URL, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            
        version = data.get(platform, {}).get(channel)
        if not version:
            raise ValueError(f"無法找到 {platform} 平台的 {channel} 版本")
            
        cdn_root = data.get('cdn_root', 'https://www.minecraft.net/bedrockdedicatedserver')
        # 組裝下載網址 (例如：https://www.minecraft.net/bedrockdedicatedserver/bin-linux/bedrock-server-1.26.12.2.zip)
        bin_path = f"bin-{platform}"
        # Windows 版檔名通常是 bedrock-server-1.x.x.zip 或類似，這裡以通用格式為主
        download_url = f"{cdn_root}/{bin_path}/bedrock-server-{version}.zip"
        
        return {
            "version": version,
            "download_url": download_url,
            "platform": platform,
            "channel": channel
        }
    except Exception as e:
        print(f"Fetch BDS version failed: {e}")
        return None

if __name__ == "__main__":
    # 測試執行
    info = get_latest_bds_info()
    if info:
        print(f"最新穩定版 ({info['platform']}): {info['version']}")
        print(f"下載連結: {info['download_url']}")
    else:
        print("獲取失敗")
