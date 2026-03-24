
import asyncio
import asyncpg
import os
import json
import pickle
from dotenv import load_dotenv

load_dotenv("/home/terraria/servers/.env")
DATABASE_URL = os.getenv("DATABASE_URL")

# Path to old memory files
MEMORY_JSON = "/home/terraria/servers/discord_bot/data/hihi/memory.json"
CHAT_HISTORY_PKL = "/home/terraria/servers/discord_bot/data/chat_history.pkl"

async def migrate_db():
    print(f"🚀 Starting Migration on: {DATABASE_URL}")
    conn = await asyncpg.connect(DATABASE_URL)
    
    try:
        # 1. Create Extensions
        print("📦 Enabling vector extension...")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        # 2. Create New Tables
        print("🔨 Creating new tables...")
        
        # Table: facts (Core Facts)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS facts (
                id SERIAL PRIMARY KEY,
                user_id TEXT NOT NULL,
                fact TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                embedding vector(768)
            );
        """)

        # Table: chat_history (Full Logs)
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS chat_history (
                id SERIAL PRIMARY KEY,
                session_id TEXT, 
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
            );
        """)

        # Table: memories (Long Term) - Upgrade Exisitng
        # Check if 'memory_store' exists
        table_exists = await conn.fetchval("SELECT to_regclass('public.memory_store');")
        if table_exists:
            print("⚠️ 'memory_store' exists, migrating data to 'memories'...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT,
                    content TEXT,
                    type TEXT DEFAULT 'observation', -- observation / reflection
                    importance INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    embedding vector(768)
                );
            """)
            
            # Migrate old data
            await conn.execute("""
                INSERT INTO memories (user_name, content, created_at, embedding)
                SELECT user_name, content, created_at, embedding FROM memory_store;
            """)
            print("✅ Data migrated to 'memories'. Dropping old 'memory_store'...")
            await conn.execute("DROP TABLE memory_store;")
        else:
            print("🆕 Creating 'memories' table...")
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS memories (
                    id SERIAL PRIMARY KEY,
                    user_name TEXT,
                    content TEXT,
                    type TEXT DEFAULT 'observation',
                    importance INTEGER DEFAULT 1,
                    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                    embedding vector(768)
                );
            """)

        # 3. Migrate File Memories
        # Import memory.json (Facts)
        if os.path.exists(MEMORY_JSON):
            print("📂 Importing memory.json...")
            with open(MEMORY_JSON, 'r') as f:
                data = json.load(f)
                for uid, info in data.items():
                    facts = info.get('facts', [])
                    for fact in facts:
                        # Note: We won't generate embeddings here to save time/cost. 
                        # They will be null for now.
                        await conn.execute(
                            "INSERT INTO facts (user_id, fact) VALUES ($1, $2)",
                            str(uid), fact
                        )
            print(f"✅ Imported facts for {len(data)} users.")

        # Import chat_history.pkl
        if os.path.exists(CHAT_HISTORY_PKL):
            print("start importing chat history")
            try:
                with open(CHAT_HISTORY_PKL, 'rb') as f:
                    history = pickle.load(f)
                    # format check: [{'role': 'user', 'parts': [{'text': 'hi'}]}, ...]
                    count = 0
                    for msg in history:
                        role = msg.get('role')
                        parts = msg.get('parts', [])
                        text = "".join([p.get('text', '') for p in parts])
                        if text:
                            await conn.execute(
                                "INSERT INTO chat_history (role, content) VALUES ($1, $2)",
                                role, text
                            )
                            count += 1
                    print(f"✅ Imported {count} chat messages.")
            except Exception as e:
                print(f"❌ Failed to import chat history log: {e}")

        print("\n🎉 Migration Complete!")
        
    except Exception as e:
        print(f"❌ Migration Failed: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(migrate_db())
