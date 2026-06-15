import os
import asyncio
from dotenv import load_dotenv
import asyncpg

# 載入環境變數
load_dotenv("/home/hi6688/servers/.env")

async def migrate_memories():
    """
    執行舊記憶資料的遷移，將 payload 內純數字的 user_id 加上 '_global' 後綴
    """
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("❌ 找不到 DATABASE_URL 環境變數。")
        return
    
    # 將 postgresql 連線協定標準化
    cleaned_db_url = db_url.replace("postgres://", "postgresql://")
    print("🔌 正在連線至資料庫...")
    
    conn = await asyncpg.connect(cleaned_db_url)
    try:
        # 1. 查詢有多少符合條件的舊資料
        # 匹配條件：payload 中的 user_id 欄位是 17 到 20 位的純數字 (Discord ID)
        check_query = """
            SELECT COUNT(*) 
            FROM hihi_mem0_facts 
            WHERE (payload ->> 'user_id') ~ '^[0-9]{17,20}$'
        """
        old_records_count = await conn.fetchval(check_query)
        print(f"📊 偵測到 {old_records_count} 筆符合遷移條件的舊記憶資料。")
        
        if old_records_count == 0:
            print("✨ 沒有需要遷移的舊格式資料。")
            return
            
        # 2. 執行更新
        # 將 payload 中的 user_id 加上 '_global' 後綴
        update_query = """
            UPDATE hihi_mem0_facts 
            SET payload = jsonb_set(payload, '{user_id}', to_jsonb((payload ->> 'user_id') || '_global'))
            WHERE (payload ->> 'user_id') ~ '^[0-9]{17,20}$'
            RETURNING id, payload ->> 'user_id' AS new_user_id
        """
        print("💾 正在將舊 user_id 遷移至 '_global' 命名空間...")
        updated_rows = await conn.fetch(update_query)
        
        print(f"✅ 成功遷移了 {len(updated_rows)} 筆資料！")
        for idx, row in enumerate(updated_rows):
            print(f"  > [{idx+1}] ID: {row['id']} -> 新的 user_id: {row['new_user_id']}")
            
    except Exception as error:
        print(f"❌ 遷移過程中發生錯誤: {error}")
    finally:
        await conn.close()
        print("🔌 資料庫連線已關閉。")

if __name__ == "__main__":
    asyncio.run(migrate_memories())
