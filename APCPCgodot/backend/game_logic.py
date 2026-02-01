from typing import List, Optional
import random
from game_models import BattleState, GamePhase, PlayerState, Pokemon, ActionType, Item

# --- 初始化邏輯 ---
def initialize_battle(room_id: str, p1_id: str, p2_id: str) -> BattleState:
    """建立全新的對戰狀態"""
    p1 = PlayerState(player_id=p1_id)
    p2 = PlayerState(player_id=p2_id)
    
    # [GDD] 初始選秀: 這裡暫時先隨機塞 6 隻給雙方 (為了快速測試)
    # 未來應該要實作 Draft Phase
    for i in range(6):
        p1.roster.append(_create_test_pokemon(f"p1_poke_{i}", "pikachu"))
        p2.roster.append(_create_test_pokemon(f"p2_poke_{i}", "bulbasaur"))
        
    return BattleState(
        room_id=room_id,
        phase=GamePhase.SETUP,
        player1=p1,
        player2=p2
    )

def _create_test_pokemon(uid: str, species: str) -> Pokemon:
    return Pokemon(
        id=uid,
        species_id=species,
        name=species.capitalize(),
        hp=100,
        max_hp=100,
        sp=3,
        evolution_threshold=50 # 測試用門檻
    )

# --- 核心機制：治療進化 (Heal-to-Evolve) ---
def apply_healing(pokemon: Pokemon, amount: int) -> dict:
    """處理治療、溢出與進化進度。回傳 log 資訊。"""
    old_hp = pokemon.hp
    
    # 1. 基礎補血
    pokemon.hp += amount
    
    # 2. 計算溢出 (Overheal)
    overheal_amount = 0
    if pokemon.hp > pokemon.max_hp:
        overheal_amount = pokemon.hp - pokemon.max_hp
        pokemon.hp = pokemon.max_hp # 修正回滿血
        
    # 3. 累積進化進度 ([GDD] 滿血溢出照樣算)
    # 有效治療(補進去的) + 溢出治療
    effective_heal = pokemon.hp - old_hp
    total_progress = effective_heal + overheal_amount
    
    pokemon.evolution_progress += total_progress
    pokemon.overheal += overheal_amount # 暫存溢出量 (為了進化後繼承)

    # 4. 檢查是否可進化
    can_evolve = pokemon.evolution_progress >= pokemon.evolution_threshold
    
    return {
        "target": pokemon.name,
        "heal": effective_heal,
        "overheal": overheal_amount,
        "progress": pokemon.evolution_progress,
        "can_evolve": can_evolve
    }

def execute_evolution(pokemon: Pokemon):
    """執行進化 ([GDD] 手動點擊後)"""
    if pokemon.evolution_progress < pokemon.evolution_threshold:
        return False
        
    # 數值提升 (假設 MaxHP + 50)
    pokemon.max_hp += 50
    # [GDD] HP 繼承: 原HP + 溢出量 (不自動補滿)
    pokemon.hp = pokemon.hp + pokemon.overheal
    if pokemon.hp > pokemon.max_hp:
        pokemon.hp = pokemon.max_hp
        
    # 重置進度
    pokemon.evolution_progress = 0
    pokemon.overheal = 0
    # pokemon.name = "Raichu" (未來需查表變更 ID)
    
    return True

# --- 狀態機循環 (Game Loop) ---
def try_advance_phase(state: BattleState):
    """檢查是否滿足條件進入下一階段"""
    
    # [DEV] 暫時允許單人測試：只要 P1 準備好就推進 (正式版請改回 and state.player2.is_ready)
    if not (state.player1.is_ready): 
    # if not (state.player1.is_ready and state.player2.is_ready):
        return
        
    if state.phase == GamePhase.SETUP:
        state.phase = GamePhase.SUPPLY
        _process_supply_phase(state)
        
    elif state.phase == GamePhase.SUPPLY:
        state.phase = GamePhase.TACTICS
        # 清空上一回合的 Actions
        state.p1_actions = []
        state.p2_actions = []
        
    elif state.phase == GamePhase.TACTICS:
        state.phase = GamePhase.COMBAT
        _resolve_combat_phase(state)
        
    elif state.phase == GamePhase.COMBAT:
        state.turn_count += 1
        state.phase = GamePhase.SUPPLY # 回到補給
        _process_supply_phase(state)
        
    # 重置 Ready 旗標
    state.player1.is_ready = False
    state.player2.is_ready = False

def _process_supply_phase(state: BattleState):
    """[GDD] 派發道具、生成野生怪"""
    
    for player in [state.player1, state.player2]:
        # 1. 發送 2 個隨機道具
        # (這裡先用測試道具，未來建立 ItemLibrary)
        new_items = [
            Item(id="potion", name="Potion", effect_type="HEAL", value=30),
            Item(id="super_potion", name="Super Potion", effect_type="HEAL", value=60)
        ]
        
        # 背包上限 10 個
        for item in new_items:
            if len(player.items) < 10:
                player.items.append(item)
                
        # 2. 生成野生寶可夢 (捕捉二選一)
        # 隨機生成一隻
        species_pool = ["charmander", "squirtle", "bulbasaur", "pikachu", "eevee"]
        random_species = random.choice(species_pool)
        
        # 確保 unique ID
        wild_id = f"wild_{state.turn_count}_{player.player_id}"
        player.wild_encounter = _create_test_pokemon(wild_id, random_species)
        
    state.combat_log.append(f"--- Supply Phase: Wild Pokemons appeared! ---")

def handle_player_action(state: BattleState, player_id: str, action_data: dict):
    """處理玩家即時指令 (Supply/Tactics)"""
    
    # 判斷是哪個玩家
    player = state.player1 if state.player1.player_id == player_id else state.player2
    
    # [Supply Phase] 捕捉邏輯
    if state.phase == GamePhase.SUPPLY:
        if action_data.get("type") == "CATCH":
            should_keep = action_data.get("keep", False)
            replace_index = action_data.get("replace_index") # [GDD] 捕捉需指定替換對象
            
            if should_keep and player.wild_encounter:
                # 檢查是否指定了有效的替換位置 (必須是備戰區 >= 2)
                if replace_index is not None and 2 <= replace_index < len(player.roster):
                    old_poke = player.roster[replace_index]
                    
                    # 執行替換
                    player.wild_encounter.id = f"p{player.player_id[-1]}_new_{state.turn_count}" # 重新編號
                    player.roster[replace_index] = player.wild_encounter
                    
                    state.combat_log.append(f"{player.player_id} caught {player.wild_encounter.name}, replacing {old_poke.name}!")
                else:
                    # 雖然 UX 應該擋住，但後端還是要防呆
                     # 如果滿員但沒指定替換，則此為無效操作 (或視為放棄)
                    state.combat_log.append(f"{player.player_id} capture failed: Invalid replace index or roster full.")
                    # ⚠️ 這裡如果失敗，是否要讓玩家重選？
                    # 為了簡化流程，失敗也視為放棄，或者可以 return 不做任何事讓前端 retry
                    return 
            else:
                state.combat_log.append(f"{player.player_id} passed on {player.wild_encounter.name if player.wild_encounter else 'nothing'}.")
                
            # 清除野生怪 (表示已處理)
            player.wild_encounter = None
            
            # [UX] 捕捉後自動 Ready (簡化流程)
            player.is_ready = True
            
    # [Tactics Phase] 戰術邏輯 (Swap, Evolve, Item)
    elif state.phase == GamePhase.TACTICS:
        action_type = action_data.get("type")
        
        if action_type == "SWAP":
            src = action_data.get("src_index")
            dst = action_data.get("dst_index")
            
            # 簡易驗證
            if src is not None and dst is not None:
                if 0 <= src < len(player.roster) and 0 <= dst < len(player.roster):
                    # Python 交換大法
                    player.roster[src], player.roster[dst] = player.roster[dst], player.roster[src]
                    state.combat_log.append(f"{player.player_id} swapped {player.roster[dst].name} with {player.roster[src].name}")
                else:
                    state.combat_log.append(f"{player.player_id} swap failed: Invalid index")
                    
        elif action_type == "ITEM":
            item_index = action_data.get("item_index")
            target_index = action_data.get("target_index")
            
            if item_index is not None and 0 <= item_index < len(player.items) and \
               target_index is not None and 0 <= target_index < len(player.roster):
               
               item = player.items[item_index]
               target = player.roster[target_index]
               
               if item.effect_type == "HEAL":
                   result = apply_healing(target, item.value)
                   state.combat_log.append(f"{player.player_id} used {item.name} on {target.name}: +{result['heal']} HP")
                   # Remove item
                   player.items.pop(item_index)
                   
        elif action_type == "EVOLVE":
            target_index = action_data.get("target_index")
            if target_index is not None and 0 <= target_index < len(player.roster):
                target = player.roster[target_index]
                if execute_evolution(target):
                    state.combat_log.append(f"{player.player_id} evolved {target.name}!")
                else:
                    state.combat_log.append(f"{player.player_id} evolution failed: Not enough progress.")

        elif action_type == "ATTACK":
            # 攻擊指令不立即執行，而是存入 Action Queue 等待結算
            # payload: { "skill_id": "tackle", "target_index": 0 }
            skill_id = action_data.get("skill_id", "tackle")
            target_index = action_data.get("target_index", 0)
            src_index = action_data.get("src_index", 0) # 哪隻怪發動攻擊
            
            # 存入暫存 (分辨是 P1 還是 P2)
            action_record = {
                "type": "ATTACK",
                "player_id": player_id,
                "src_index": src_index,
                "skill_id": skill_id,
                "target_index": target_index
            }
            
            if player_id == state.player1.player_id:
                state.p1_actions.append(action_record)
            else:
                state.p2_actions.append(action_record)
                
            state.combat_log.append(f"{player_id} locked in attack!")
            player.is_ready = True # 攻擊鎖定後就 Ready

def _resolve_combat_phase(state: BattleState):
    """[GDD] 戰鬥演示與結算"""
    # 這是最複雜的部分：排序 Action -> 計算傷害 -> 寫入 Log
    state.combat_log.append(f"--- Turn {state.turn_count} Combat Resolution ---")
    
    # 合併雙方指令 (未來需依 Speed 排序)
    all_actions = state.p1_actions + state.p2_actions
    
    for action in all_actions:
        if action["type"] == "ATTACK":
            attacker_pid = action["player_id"]
            target_idx = action["target_index"]
            skill = action["skill_id"]
            
            # 決定攻守方
            attacker_state = state.player1 if attacker_pid == state.player1.player_id else state.player2
            defender_state = state.player2 if attacker_pid == state.player1.player_id else state.player1
            
            # 檢查目標是否存在
            if target_idx < len(defender_state.roster):
                target = defender_state.roster[target_idx]
                attacker = attacker_state.roster[action["src_index"]]
                
                # 計算傷害 (MVP: 固定 10 點)
                damage = 10
                target.hp -= damage
                if target.hp < 0: target.hp = 0
                
                state.combat_log.append(f"{attacker.name} used {skill} on {target.name}! (-{damage} HP)")
                
                if target.hp == 0:
                    state.combat_log.append(f"{target.name} fainted!")
            else:
                state.combat_log.append(f"{attacker_pid}'s attack missed (Invalid Target)!")
    
    # 清空 Actions
    state.p1_actions = []
    state.p2_actions = []
