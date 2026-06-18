import os
import asyncio
import json
from dotenv import load_dotenv
import asyncpg
from honcho import Honcho

# 載入環境變數
load_dotenv("/home/hi6688/servers/.env")

async def migrate_facts():
    # 讀取資料庫連線 URL
    # db_url: 資料庫連接字串
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("錯誤：環境變數中未設定 DATABASE_URL！")
        return
    
    # 讀取本地自建 Honcho Server 的 Base URL
    # honcho_base_url: 本地自建端點位置
    honcho_base_url = os.getenv("HONCHO_BASE_URL", "http://localhost:8000")
    
    # 讀取 Honcho API Key (本地免驗證模式下可為選填)
    # honcho_key: 驗證金鑰
    honcho_key = os.getenv("HONCHO_API_KEY")

    # 將 postgres:// 協議轉換為 asyncpg 所需的 postgresql://
    # cleaned_url: 格式化後的連接字串
    cleaned_url = db_url.replace("postgres://", "postgresql://")
    
    # 初始化 Honcho 客戶端，指向本地端點
    # honcho_client: 指向自建服務端的 Honcho 實例
    if honcho_key:
        honcho_client = Honcho(api_key=honcho_key, base_url=honcho_base_url)
        print(f"初始化 Honcho 客戶端 (使用金鑰驗證，端點: {honcho_base_url})...")
    else:
        honcho_client = Honcho(base_url=honcho_base_url)
        print(f"初始化 Honcho 客戶端 (使用免驗證模式，端點: {honcho_base_url})...")
    
    print("正在建立 PostgreSQL 連線...")
    conn = await asyncpg.connect(cleaned_url)
    
    try:
        # 從資料庫中讀取所有的記憶事實
        # rows: 記憶事實原始數據列
        rows = await conn.fetch("SELECT payload FROM hihi_mem0_facts")
        print(f"成功自資料庫撈取到 {len(rows)} 條記憶事實。")
        
        # 遍歷事實數據並寫入本地 Honcho
        # success_count: 遷移成功的數量
        success_count = 0
        
        for idx, row in enumerate(rows):
            # 解析 jsonb 格式的 payload
            # payload: 記憶事實載荷
            payload = json.loads(row["payload"])
            
            # fact_text: 事實陳述內容
            fact_text = payload.get("data")
            
            # user_id: 對應的用戶識別碼
            user_id = payload.get("user_id", "_global")
            
            if not fact_text:
                continue
            
            # 清理 user_id 以符合 Honcho 的 Peer ID 正則規範 (^[a-zA-Z0-9_-]+$)
            # clean_peer_id: 符合正則的 peer 識別碼
            clean_peer_id = "".join(c for c in user_id if c.isalnum() or c in ("-", "_"))
            if not clean_peer_id:
                clean_peer_id = "global_user"
                
            try:
                # 獲取或建立 Peer 實體
                # peer: Honcho 使用者 Peer 實例
                peer = honcho_client.peer(clean_peer_id)
                
                # 獲取 Peer 自我結論範疇
                # conclusions_scope: 結論範疇實例
                conclusions_scope = peer.conclusions_of(clean_peer_id)
                
                # 在本地 Honcho 中建立結論 (Conclusions)
                conclusions_scope.create([{
                    "content": fact_text.strip()
                }])
                
                success_count += 1
                if success_count % 10 == 0 or success_count == len(rows):
                    print(f"已成功遷移 {success_count}/{len(rows)} 條記憶...")
            except Exception as e:
                print(f"第 {idx} 條遷移失敗 (User: {clean_peer_id})，錯誤：{e}")
                
        print(f"\n🎉 記憶遷移完成！成功遷移 {success_count} 條事實至本地 Honcho Server。")
        
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_facts())
