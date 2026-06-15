import os
import asyncio
import json
from dotenv import load_dotenv
import asyncpg

load_dotenv("/home/hi6688/servers/.env")

async def verify():
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        print("DATABASE_URL is not set.")
        return
    
    cleaned_db_url = db_url.replace("postgres://", "postgresql://")
    conn = await asyncpg.connect(cleaned_db_url)
    try:
        # 1. 驗證是否還有純數字 user_id 殘留
        remains_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM hihi_mem0_facts 
            WHERE (payload ->> 'user_id') ~ '^[0-9]{17,20}$'
        """)
        print(f"🔍 [驗證 1] 殘留的純數字 user_id 資料筆數: {remains_count} (預期應為 0)")

        # 2. 驗證 691639108212228096_global 的資料筆數
        global_count = await conn.fetchval("""
            SELECT COUNT(*) 
            FROM hihi_mem0_facts 
            WHERE payload ->> 'user_id' = '691639108212228096_global'
        """)
        print(f"🔍 [驗證 2] 691639108212228096_global 的總資料筆數: {global_count} (預期應至少有 5 筆)")

        # 3. 列出前 3 筆 global 記憶做最終確認
        rows = await conn.fetch("""
            SELECT id, payload 
            FROM hihi_mem0_facts 
            WHERE payload ->> 'user_id' = '691639108212228096_global'
            LIMIT 3
        """)
        print("🔍 [驗證 3] 部分遷移後的資料內容樣貌:")
        for idx, row in enumerate(rows):
            payload_str = row['payload']
            payload = json.loads(payload_str) if isinstance(payload_str, str) else payload_str
            print(f"  > 記憶 [{idx+1}] ID: {row['id']}")
            print(f"    * payload -> user_id: {payload.get('user_id')}")
            print(f"    * payload -> data: {payload.get('data')[:60]}...")

    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(verify())
