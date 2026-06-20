import requests
import json

# 已將運維主管與機器人的 Dashboard Token 進行物理隔離，使用不同的憑證
admin_token = "8a24244f44a455a2c9a0835528734f2a"
hihi_token = "2a1a462e6c7b2594fcf73cf0c7de0b74"

def check_status(port, name, token):
    url = f"http://127.0.0.1:{port}/api/status"
    headers = {
        "Authorization": f"Bearer {token}"
    }
    try:
        resp = requests.get(url, headers=headers, timeout=5)
        print(f"=== {name} (Port {port}) ===")
        print(f"Status Code: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(json.dumps(data, indent=2, ensure_ascii=False))
        else:
            print(resp.text)
    except Exception as e:
        print(f"Error checking {name}: {e}")

if __name__ == "__main__":
    check_status(9119, "Server Admin Dashboard", admin_token)
    print("\n" + "="*40 + "\n")
    check_status(9120, "HiHi Dashboard", hihi_token)
