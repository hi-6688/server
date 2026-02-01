import os
from typing import Optional
from sqlmodel import Field, SQLModel, create_engine, Session
from dotenv import load_dotenv

load_dotenv()

class GameRoom(SQLModel, table=True):
    id: str = Field(primary_key=True)  # Room Code (e.g. "A1B2")
    host_token: str
    guest_token: Optional[str] = None
    status: str = "waiting"  # "waiting", "playing", "finished"

# ... rest of the file ...

# 讀取環境變數，若無則預設為 SQLite
database_url = os.getenv("DATABASE_URL", "sqlite:///dev.db")

# 判斷是否為 PostgreSQL (需要不同的參數)
connect_args = {}
if "sqlite" in database_url:
    connect_args = {"check_same_thread": False}

# 建立資料庫引擎
engine = create_engine(database_url, echo=True, connect_args=connect_args)

def create_db_and_tables():
    SQLModel.metadata.create_all(engine)

def get_session():
    with Session(engine) as session:
        yield session
