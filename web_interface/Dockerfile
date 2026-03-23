FROM python:3.10-slim

WORKDIR /app

# 複製並安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 原始碼會透過 docker-compose volume 掛載到 /app
# 預設執行 API 分發器
CMD ["python3", "-u", "api.py"]
