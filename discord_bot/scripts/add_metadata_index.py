
import asyncio
import os
import asyncpg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

async def add_metadata_index():
    if not DATABASE_URL:
        print("❌ DATABASE_URL is not set.")
        return

    conn = await asyncpg.connect(DATABASE_URL)
    try:
        print("🔧 Adding GIN Index to 'memories.metadata'...")
        
        # Create GIN index for JSONB column
        # "idx_memories_metadata"
        query = """
        CREATE INDEX IF NOT EXISTS idx_memories_metadata 
        ON memories USING GIN (metadata);
        """
        
        await conn.execute(query)
        print("✅ GIN Index created successfully on 'memories(metadata)'!")
        
        # Also create Full Text Search Index (TSVECTOR) for content
        # "idx_memories_content_fts"
        # We use 'english' configuration for now, or 'simple' for general purpose
        # For mixed Chinese/English, 'simple' is often safer or use 'jieba' if installed (usually not in default pg).
        # We'll use 'simple' to allow rudimentary matching.
        print("🔧 Adding Full-Text Search Index to 'memories.content'...")
        query_fts = """
        CREATE INDEX IF NOT EXISTS idx_memories_content_fts 
        ON memories USING GIN (to_tsvector('simple', content));
        """
        await conn.execute(query_fts)
        print("✅ Full-Text Index created successfully on 'memories(content)'!")

    except Exception as e:
        print(f"❌ Error creating index: {e}")
    finally:
        await conn.close()

if __name__ == "__main__":
    asyncio.run(add_metadata_index())
