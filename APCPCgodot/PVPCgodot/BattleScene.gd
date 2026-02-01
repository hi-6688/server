extends Control

@onready var status_label = $StatusLabel
@onready var p1_roster_list = $P1Roster
@onready var p1_items_list = $P1Items
@onready var p2_info = $P2Info
@onready var ready_button = $ReadyButton
@onready var catch_button = $CatchButton
@onready var pass_button = $PassButton
@onready var swap_button = $SwapButton
@onready var use_item_button = $UseItemButton
@onready var evolve_button = $EvolveButton
@onready var attack_p1_btn = $AttackP1Button
@onready var attack_p2_btn = $AttackP2Button
@onready var combat_log = $CombatLog

func _ready():
	print("BattleScene 已就緒，正在連接信號...")
	NetworkManager.state_updated.connect(_on_state_updated)
	
	ready_button.pressed.connect(_on_ready_pressed)
	catch_button.pressed.connect(func(): _on_action_pressed("CATCH", true))
	pass_button.pressed.connect(func(): _on_action_pressed("CATCH", false))
	swap_button.pressed.connect(_on_swap_pressed)
	use_item_button.pressed.connect(_on_use_item_pressed)
	evolve_button.pressed.connect(_on_evolve_pressed)
	attack_p1_btn.pressed.connect(func(): _on_attack_pressed(0)) # Atk Enemy 1
	attack_p2_btn.pressed.connect(func(): _on_attack_pressed(1)) # Atk Enemy 2
	
	status_label.text = "等待連線..."

func _on_attack_pressed(target_idx: int):
	# 預設使用第一隻 Active (Index 0) 攻擊，除非玩家選了第二隻 (Index 1)
	var src_index = 0
	var selected = p1_roster_list.get_selected_items()
	if selected.size() > 0 and selected[0] == 1:
		src_index = 1
		
	# 檢查是否選擇了 Bench 怪 (不能攻擊)
	if selected.size() > 0 and selected[0] >= 2:
		status_label.text += "\n[Error] Bench pokemon cannot attack!"
		return
		
	NetworkManager.send_command("ACTION", {
		"type": "ATTACK",
		"skill_id": "Tackle", # MVP 固定招式
		"src_index": src_index,
		"target_index": target_idx
	})
	
	# 攻擊後自動 Ready (後端邏輯)，前端先把按鈕關掉避免重複按
	attack_p1_btn.visible = false
	attack_p2_btn.visible = false

# ... (省略中間未變更的 functions) ...


func _on_ready_pressed():
	NetworkManager.send_command("READY")
	ready_button.disabled = true
	ready_button.text = "Waiting..."

func _on_action_pressed(action_type: String, keep: bool):
	var payload = {"type": action_type, "keep": keep}
	
	if keep:
		var selected = p1_roster_list.get_selected_items()
		if selected.size() == 0:
			status_label.text += "\n[Error] Select a BENCH pokemon to replace!"
			return
		var replace_idx = selected[0]
		if replace_idx < 2:
			status_label.text += "\n[Error] Cannot replace Active pokemon!"
			return
		payload["replace_index"] = replace_idx
	
	NetworkManager.send_command("ACTION", payload)
	catch_button.visible = false
	pass_button.visible = false

func _on_swap_pressed():
	var selected = p1_roster_list.get_selected_items()
	if selected.size() == 0: return
	var src_index = selected[0]
	var dst_index = 0 if src_index != 0 else 1
	NetworkManager.send_command("ACTION", {"type": "SWAP", "src_index": src_index, "dst_index": dst_index})

func _on_use_item_pressed():
	# 需選中一個道具 & 一隻寶可夢
	var item_sel = p1_items_list.get_selected_items()
	var poke_sel = p1_roster_list.get_selected_items()
	
	if item_sel.size() == 0 or poke_sel.size() == 0:
		status_label.text += "\n[Error] Select an ITEM and a POKEMON!"
		return
		
	NetworkManager.send_command("ACTION", {
		"type": "ITEM",
		"item_index": item_sel[0],
		"target_index": poke_sel[0]
	})

func _on_evolve_pressed():
	var poke_sel = p1_roster_list.get_selected_items()
	if poke_sel.size() == 0: return
	
	NetworkManager.send_command("ACTION", {
		"type": "EVOLVE",
		"target_index": poke_sel[0]
	})

func _on_state_updated(state: GameModels.BattleState):
	# 1. Status Label
	var status_text = "Phase: %s | Turn: %d" % [state.phase, state.turn_count]
	if state.phase == "supply" and state.player1 and state.player1.wild_encounter:
		status_text += "\n\n[!] Wild %s appeared!" % state.player1.wild_encounter.name
	
	# [Optimization] 只有文字改變時才更新
	if status_label.text != status_text:
		status_label.text = status_text
	
	# 2. Buttons Visibility
	ready_button.visible = false
	catch_button.visible = false
	pass_button.visible = false
	swap_button.visible = false
	use_item_button.visible = false
	evolve_button.visible = false
	
	if state.phase == "setup":
		ready_button.visible = true
		ready_button.text = "READY!"
	elif state.phase == "supply":
		if state.player1 and state.player1.wild_encounter:
			catch_button.visible = true
			pass_button.visible = true
	elif state.phase == "tactics":
		ready_button.visible = true
		ready_button.text = "FIGHT!"
		swap_button.visible = true
		use_item_button.visible = true
		evolve_button.visible = true
		# [Fix] 攻擊指令是在戰術階段下達的
		attack_p1_btn.visible = true
		attack_p2_btn.visible = true
	elif state.phase == "combat":
		ready_button.visible = true
		ready_button.text = "NEXT TURN"
		# Combat 只看結果，不需再攻擊
		attack_p1_btn.visible = false
		attack_p2_btn.visible = false
		
	if state.player1 and state.player1.is_ready:
		ready_button.disabled = true
		ready_button.text = "Waiting..."
	else:
		ready_button.disabled = false

	# 3. Roster List (with Evo Progress)
	var p1_roster_lines: Array[String] = []
	if state.player1:
		for i in range(state.player1.roster.size()):
			var p = state.player1.roster[i]
			var status = "[Active]" if i < 2 else "[Bench]"
			var evo_info = "[Evo: %d/%d]" % [p.evolution_progress, p.evolution_threshold]
			p1_roster_lines.append("%s %s (HP: %d) %s" % [status, p.name, p.hp, evo_info])
	_update_list_ui(p1_roster_list, p1_roster_lines)
			
	# 4. Items List
	var p1_item_lines: Array[String] = []
	if state.player1:
		for item in state.player1.items:
			p1_item_lines.append("%s (Effect: %s)" % [item.name, item.effect_type])
	_update_list_ui(p1_items_list, p1_item_lines)
			
	# 5. P2 Info
	# ... (省略 P2 邏輯)
	var p2_text = "Player 2 (Guest):\n"
	if state.player2:
		for i in range(state.player2.roster.size()):
			var p = state.player2.roster[i]
			var status = "[Active]" if i < 2 else "[Bench]"
			var hp_text = "HP: %d/%d" % [p.hp, p.max_hp]
			p2_text += "%s %s (%s)\n" % [status, p.name, hp_text]
	
	# [Optimization] 只有變動時才更新 Label
	if p2_info.text != p2_text:
		p2_info.text = p2_text
	
	# Combat Log 更新
	var new_log_text = "Combat Log:\n"
	if state.combat_log:
		for log_entry in state.combat_log:
			new_log_text += str(log_entry) + "\n"
			
	# [Optimization] 只有變動時才更新 RichTextLabel (這是最容易閃爍的元件)
	if combat_log.text != new_log_text:
		combat_log.text = new_log_text

# [NEW] 智慧更新列表，避免閃爍
func _update_list_ui(list_node: ItemList, new_lines: Array[String]):
	# 1. 調整數量 (比對現有數量 vs 目標數量)
	while list_node.item_count < new_lines.size():
		list_node.add_item("") # 先補空格
	while list_node.item_count > new_lines.size():
		list_node.remove_item(list_node.item_count - 1) # 移除多餘
		
	# 2. 更新內容 (只改有變動的文字)
	for i in range(new_lines.size()):
		if list_node.get_item_text(i) != new_lines[i]:
			list_node.set_item_text(i, new_lines[i])
