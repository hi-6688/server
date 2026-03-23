FROM python:3.10-slim

WORKDIR /app

# 安裝可能需要的系統級編譯工具
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# 複製並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 原始碼會透過 docker-compose volume 掛載到 /app
# 預設執行機器人主程式
CMD ["python3", "-u", "main.py"]
