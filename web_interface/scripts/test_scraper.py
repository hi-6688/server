import urllib.request
import re

url = "https://www.minecraft.net/en-us/download/server/bedrock"
headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}

try:
    req = urllib.request.Request(url, headers=headers)
    with urllib.request.urlopen(req) as response:
        html = response.read().decode('utf-8')
        # Search for link
        # Pattern usually: https://minecraft.azureedge.net/bin-linux/bedrock-server-1.21.51.01.zip
        match = re.search(r'https://minecraft\.azureedge\.net/bin-linux/bedrock-server-([\d\.]+)\.zip', html)
        if match:
            print(f"FOUND: {match.group(0)}")
        else:
            print("NOT FOUND")
except Exception as e:
    print(f"ERROR: {e}")
