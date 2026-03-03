"""
資料庫健康檢查腳本 (Database Health Audit)
檢查：表結構、索引、資料量、連線池狀態
"""
import asyncio
import os
import sys
import asyncpg
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL")

async def audit():
    if not DATABASE_URL:
        print("❌ DATABASE_URL not set.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    
    print("=" * 60)
    print("🔍 PostgreSQL Database Health Audit")
    print("=" * 60)
    
    # 1. 表列表 (Tables)
    print("\n📊 [1] Tables:")
    tables = await conn.fetch("""
        SELECT table_name FROM information_schema.tables 
        WHERE table_schema = 'public' ORDER BY table_name
    """)
    for t in tables:
        count = await conn.fetchval(f"SELECT COUNT(*) FROM {t['table_name']}")
        print(f"  - {t['table_name']}: {count} rows")
    
    # 2. 索引列表 (Indexes)
    print("\n📇 [2] Indexes:")
    indexes = await conn.fetch("""
        SELECT indexname, tablename, indexdef 
        FROM pg_indexes 
        WHERE schemaname = 'public'
        ORDER BY tablename, indexname
    """)
    for idx in indexes:
        print(f"  - [{idx['tablename']}] {idx['indexname']}")
        print(f"    {idx['indexdef'][:120]}")
    
    # 3. 欄位結構 (Column Details)
    print("\n🏗️ [3] Column Details:")
    for t in tables:
        cols = await conn.fetch("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = $1
            ORDER BY ordinal_position
        """, t['table_name'])
        print(f"\n  📋 {t['table_name']}:")
        for c in cols:
            nullable = "NULL" if c['is_nullable'] == 'YES' else "NOT NULL"
            default = f" DEFAULT {c['column_default'][:30]}" if c['column_default'] else ""
            print(f"    - {c['column_name']}: {c['data_type']} ({nullable}){default}")
    
    # 4. pgvector 擴展 (Extensions)
    print("\n🧩 [4] Extensions:")
    exts = await conn.fetch("SELECT extname, extversion FROM pg_extension")
    for ext in exts:
        print(f"  - {ext['extname']} v{ext['extversion']}")
    
    # 5. 連線數 (Active Connections)
    print("\n🔌 [5] Active Connections:")
    conns = await conn.fetchval("SELECT COUNT(*) FROM pg_stat_activity WHERE datname = current_database()")
    max_conns = await conn.fetchval("SHOW max_connections")
    print(f"  - Active: {conns} / Max: {max_conns}")
    
    # 6. DB 大小
    print("\n💾 [6] Database Size:")
    size = await conn.fetchval("SELECT pg_size_pretty(pg_database_size(current_database()))")
    print(f"  - Total: {size}")
    
    # 7. 各表大小
    print("\n📏 [7] Table Sizes:")
    for t in tables:
        tsize = await conn.fetchval(f"SELECT pg_size_pretty(pg_total_relation_size('{t['table_name']}'))")
        print(f"  - {t['table_name']}: {tsize}")

    await conn.close()
    print("\n" + "=" * 60)
    print("✅ Audit Complete")

if __name__ == "__main__":
    asyncio.run(audit())
