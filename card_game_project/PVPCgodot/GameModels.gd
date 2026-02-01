class_name GameModels extends Node

# 這個檔案負責定義與 Python 後端對應的資料結構
# 方便我們在 Godot 裡有型別提示 (Type Hinting)

class Item:
	var id: String
	var name: String
	var effect_type: String
	var value: int
	
	func _init(data: Dictionary):
		id = str(data.get("id", ""))
		name = str(data.get("name", "Unknown Item"))
		effect_type = str(data.get("effect_type", ""))
		value = int(data.get("value", 0))

class Pokemon:
	var id: String
	var name: String
	var species_id: String
	var hp: int
	var max_hp: int
	var sp: int
	var evolution_progress: int
	var evolution_threshold: int
	var is_active: bool
	
	func _init(data: Dictionary):
		id = data.get("id", "")
		name = data.get("name", "Unknown")
		species_id = data.get("species_id", "")
		hp = int(data.get("hp", 0))
		max_hp = int(data.get("max_hp", 0))
		sp = int(data.get("sp", 0))
		evolution_progress = int(data.get("evolution_progress", 0))
		evolution_threshold = int(data.get("evolution_threshold", 0))
		is_active = data.get("is_active", false)

class PlayerState:
	var player_id: String
	var roster: Array[Pokemon] = []
	var items: Array[Item] = [] # [NEW] 道具清單
	var wild_encounter: Pokemon # [NEW] 野生遭遇
	var is_ready: bool
	
	func _init(data: Dictionary):
		player_id = str(data.get("player_id", ""))
		is_ready = data.get("is_ready", false)
		
		# 解析 Pokemon 陣列
		var roster_data = data.get("roster", [])
		for p_data in roster_data:
			roster.append(Pokemon.new(p_data))
			
		# 解析 Items 陣列
		var items_data = data.get("items", [])
		for i_data in items_data:
			items.append(Item.new(i_data))
			
		# 解析 野生遭遇
		var wild_data = data.get("wild_encounter")
		if wild_data and wild_data is Dictionary:
			wild_encounter = Pokemon.new(wild_data)

class BattleState:
	var room_id: String
	var phase: String
	var turn_count: int
	var player1: PlayerState
	var player2: PlayerState
	var combat_log: Array = [] # [NEW] 戰鬥紀錄
	
	func _init(data: Dictionary):
		if data == null: data = {} # 防呆機制
		
		# 安全讀取
		room_id = str(data.get("room_id", ""))
		phase = str(data.get("phase", "setup"))
		turn_count = int(data.get("turn_count", 1))
		combat_log = data.get("combat_log", [])
		
		var p1_data = data.get("player1", {})
		if p1_data is Dictionary:
			player1 = PlayerState.new(p1_data)
			
		var p2_data = data.get("player2", {})
		if p2_data is Dictionary:
			player2 = PlayerState.new(p2_data)

# 靜態解析函數
static func parse_state(json_dict: Dictionary) -> BattleState:
	return BattleState.new(json_dict)
