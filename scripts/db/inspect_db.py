
import asyncio
import asyncpg
import os
from dotenv import load_dotenv

# Load .env
load_dotenv("/home/terraria/servers/.env")

DATABASE_URL = os.getenv("DATABASE_URL")

async def inspect_db():
    print(f"Connecting to DB...")
    try:
        conn = await asyncpg.connect(DATABASE_URL)
        print("✅ Connected.\n")
        
        # 1. List all tables
        print("📊 Tables:")
        rows = await conn.fetch("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
        """)
        tables = [row['table_name'] for row in rows]
        for t in tables:
            print(f" - {t}")
            
        # 2. Check content of key tables
        # Corrected: chat_logs -> chat_history
        target_tables = ['memories', 'facts', 'chat_history']
        
        for table in target_tables:
            if table not in tables:
                print(f"\n⚠️ Table '{table}' not found in DB.")
                continue

            print(f"\n🧠 Content of '{table}' (Top 5):")
            
            # Inspect Columns first
            cols = await conn.fetch(f"""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = '{table}'
            """)
            col_names = [c['column_name'] for c in cols]
            print(f"   Columns: {col_names}")
            
            try:
                # Use simple SELECT * LIMIT 5
                rows = await conn.fetch(f"SELECT * FROM {table} LIMIT 5")
                if not rows:
                    print("   (Empty)")
                for row in rows:
                    # Convert to dict for cleaner print
                    d = dict(row)
                    # Truncate long content
                    if 'content' in d and len(str(d['content'])) > 50:
                        d['content'] = str(d['content'])[:50] + "..."
                    print(f"   {d}")
            except Exception as e:
                print(f"   ⚠️ Error reading {table}: {e}")

        await conn.close()
    except Exception as e:
        print(f"❌ Connection Failed: {e}")

if __name__ == "__main__":
    asyncio.run(inspect_db())
