FROM python:3.11-slim

WORKDIR /app

# 設定環境變數：確保 Log 即時輸出 (12-Factor)
ENV PYTHONUNBUFFERED=1

# 安裝依賴
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 複製程式碼
COPY . .

# 預設啟動指令 (可被 docker-compose 或 app.yaml 覆蓋)
# 使用 exec 確保收到 SIGTERM
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8080"]
