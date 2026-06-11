import os
from google.adk.sessions.database_session_service import DatabaseSessionService # 匯入官方資料庫會話服務
from google.adk.sessions.in_memory_session_service import InMemorySessionService # 匯入官方記憶體會話服務

def get_session_service():
    """
    獲取 Google ADK 官方會話服務實例。
    優先使用環境變數中的 DATABASE_URL 對接 PostgreSQL，若無則回退至記憶體會話儲存。
    """
    db_url = os.getenv("DATABASE_URL")
    if db_url:
        try:
            # 進行非同步協議轉換與參數清理以相容 SQLAlchmey + asyncpg
            cleaned_db_url = db_url.replace("postgres://", "postgresql+asyncpg://").replace("?sslmode=require", "")
            print(f"🔌 [ADK Session] 正在初始化 DatabaseSessionService 連接 PostgreSQL: {cleaned_db_url.split('@')[-1]}")
            return DatabaseSessionService(db_url=cleaned_db_url)
        except Exception as e:
            print(f"⚠️ [ADK Session] 資料庫會話服務初始化失敗: {e}，回退至記憶體儲存。")
            return InMemorySessionService()
    else:
        print("⚠️ [ADK Session] 未配置 DATABASE_URL，回退至記憶體會話儲存。")
        return InMemorySessionService()
