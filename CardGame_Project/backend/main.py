import json
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from sqlmodel import Session
from database import create_db_and_tables, engine, GameRoom
from game_models import BattleState, PlayerState
from game_logic import initialize_battle, try_advance_phase, handle_player_action

# 設定 Logging (12-Factor: Logs as Event Streams)
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

# --- In-Memory State Manager (暫存戰鬥狀態) ---
# 注意：這在單機 Docker 可行，但在多副本 Scale-out 時需改用 Redis
active_battles: dict[str, BattleState] = {}
active_connections: dict[str, list[WebSocket]] = {}

# Lifespan: 處理啟動與關閉
@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting up...")
    create_db_and_tables()
    yield
    logger.info("Server shutting down...")

app = FastAPI(lifespan=lifespan)

@app.get("/")
def read_root():
    return {"Hello": "World"}

# Health Check
@app.get("/health")
def health_check():
    return {"status": "ok"}

@app.websocket("/ws/{room_id}")
async def websocket_endpoint(websocket: WebSocket, room_id: str, token: str = None):
    await websocket.accept()
    
    # 1. 驗證房間與身份
    active_room: GameRoom = None
    player_id: str = None
    
    with Session(engine) as session:
        active_room = session.get(GameRoom, room_id)
        if not active_room:
            await websocket.close(code=4000, reason="Invalid Room")
            return
            
        if token == active_room.host_token:
            player_id = "p1_host"
        elif token == active_room.guest_token:
            player_id = "p2_guest"
        else:
            # 暫時允許單人測試，如果 Token 不對就當作 Host (方便 Godot 測試)
            # 生產環境應改回嚴格驗證
            logger.warning(f"Unknown token, assuming Host for testing. Room: {room_id}")
            player_id = "p1_host" 

    # 2. 初始化或獲取戰鬥狀態
    if room_id not in active_battles:
        logger.info(f"Initializing new battle for Room {room_id}")
        active_battles[room_id] = initialize_battle(room_id, "p1_host", "p2_guest")
        active_connections[room_id] = []
    
    battle_state = active_battles[room_id]
    active_connections[room_id].append(websocket)

    logger.info(f"Player {player_id} connected to Room {room_id}")
    
    # 發送初始狀態給前端
    await websocket.send_json({
        "type": "STATE_UPDATE",
        "payload": battle_state.model_dump()
    })
    
    try:
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)
            logger.info(f"[{room_id}] Received from {player_id}: {message}")
            
            # --- 處理前端指令 ---
            if message.get("type") == "READY":
                # 設定該玩家準備就緒
                if player_id == "p1_host":
                    battle_state.player1.is_ready = True
                elif player_id == "p2_guest":
                    battle_state.player2.is_ready = True
                
                # 嘗試推進階段 (如果雙方都 Ready)
                try_advance_phase(battle_state)
                
                # 廣播最新狀態給所有連線者
                # (Model dump 會把整個複雜的 Pokemon/Phase 結構轉成 JSON)
                broadcast_msg = {
                    "type": "STATE_UPDATE",
                    "payload": battle_state.model_dump()
                }
                for conn in active_connections[room_id]:
                    await conn.send_json(broadcast_msg)

            elif message.get("type") == "ACTION":
                # 處理通用指令 (ACTION)
                payload = message.get("payload", {})
                handle_player_action(battle_state, player_id, payload)
                
                # 檢查是否觸發階段推進
                try_advance_phase(battle_state)
                
                # 廣播更新
                broadcast_msg = {
                    "type": "STATE_UPDATE",
                    "payload": battle_state.model_dump()
                }
                for conn in active_connections[room_id]:
                    await conn.send_json(broadcast_msg)

    except WebSocketDisconnect:
        logger.info(f"[{room_id}] Player {player_id} disconnected")
        if websocket in active_connections[room_id]:
            active_connections[room_id].remove(websocket)
