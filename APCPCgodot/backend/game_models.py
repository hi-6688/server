from typing import List, Optional
from enum import Enum
from pydantic import BaseModel
from sqlmodel import SQLModel, Field

# --- Enums (列舉狀態) ---
class GamePhase(str, Enum):
    SETUP = "setup"       # 選秀
    SUPPLY = "supply"     # 補給/捕捉
    TACTICS = "tactics"   # 戰術 (隱藏資訊)
    COMBAT = "combat"     # 戰鬥演示
    FINISHED = "finished" # 結算

class ActionType(str, Enum):
    ATTACK = "attack"
    EVOLVE = "evolve"
    ITEM = "item"
    SWAP = "swap"
    WAIT = "wait"

# --- Core Models (核心物件) ---
class Pokemon(BaseModel):
    id: str  # 唯一 ID (UUID)
    species_id: str # 種族 (例如 "pikachu")
    name: str
    
    # 數值
    hp: int
    max_hp: int
    sp: int = 3       # 預設 3
    
    # 進化機制
    overheal: int = 0         # 溢出治療量
    evolution_progress: int = 0 # 累積進化進度
    next_evolution_id: Optional[str] = None # 下一階 ID
    evolution_threshold: int = 0 # 進化門檻 (下一階 MaxHP - 當前 MaxHP)

    is_active: bool = False   # 是否在場上
    slot_index: int = -1      # 場上位置 (0,1) 或 備戰區 (-1)

class Item(BaseModel):
    id: str
    name: str
    effect_type: str  # HEAL, BOOST, REVIVE...
    value: int        # 數值

# --- Player State (玩家狀態) ---
class PlayerState(BaseModel):
    player_id: str
    roster: List[Pokemon] = [] # 隊伍 (固定 6 隻)
    items: List[Item] = []     # 背包 (上限 10)
    wild_encounter: Optional[Pokemon] = None # [GDD] 補給階段遇到的野生怪
    
    # 狀態旗標
    is_ready: bool = False     # 是否已鎖定指令
    has_retreated: bool = False # 這回合是否已撤退過 (雖然規則沒寫限制，但通常會有)

# --- Game State (全域遊戲狀態) ---
class BattleState(BaseModel):
    room_id: str
    phase: GamePhase = GamePhase.SETUP
    turn_count: int = 1
    
    player1: PlayerState
    player2: PlayerState
    
    # 戰術階段暫存指令 (隱藏資訊)
    p1_actions: List[dict] = []
    p2_actions: List[dict] = []
    
    # 戰鬥日誌 (回傳給前端播放用)
    combat_log: List[str] = [] 
