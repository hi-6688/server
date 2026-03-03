
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")
DB_URL = os.getenv("DATABASE_URL")

# Mapping: Bad Key -> Canonical Key
MAPPINGS = {
    "小煌的狗": "csr.0722_31098",
    "小煌的狗 (csr.0722_31098)": "csr.0722_31098",
    "豬豬豬豬": "piggy0326",
    "豬豬豬豬 (piggy0326)": "piggy0326",
    "魔": "moyin0907",
    "魔 (moyin0907)": "moyin0907",
    "普通的高校生": "apexdieder",
    "普通的高校生 (apexdieder)": "apexdieder",
    "Hi6688": "hi6688",
    "HiHi": "hi6688",
    "誰": "_mx9uuu",
    "誰 (_mx9uuu)": "_mx9uuu"
}

async def fix():
    if not DB_URL: return
    conn = await asyncpg.connect(DB_URL)
    try:
        print("🔧 Starting Identity Merge...")
        
        for bad_key, good_key in MAPPINGS.items():
            # 1. Check if bad key exists
            rows = await conn.fetch("SELECT fact FROM facts WHERE user_id = $1", bad_key)
            if not rows: continue
            
            print(f"👉 Merging '{bad_key}' ({len(rows)} facts) -> '{good_key}'")
            
            for r in rows:
                fact = r['fact']
                # 2. Insert into good key (ignore duplicates)
                try:
                    exists = await conn.fetchval(
                        "SELECT 1 FROM facts WHERE user_id = $1 AND fact = $2", 
                        good_key, fact
                    )
                    if not exists:
                        await conn.execute(
                            "INSERT INTO facts (user_id, fact) VALUES ($1, $2)",
                            good_key, fact
                        )
                        print(f"   [Moved] {fact[:20]}...")
                    else:
                        print(f"   [Skip] Duplicate fact.")
                except Exception as e:
                    print(f"   [Error] {e}")

            # 3. Delete bad key
            await conn.execute("DELETE FROM facts WHERE user_id = $1", bad_key)
            print(f"   ✅ Deleted '{bad_key}'")

        print("✨ Done!")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(fix())
