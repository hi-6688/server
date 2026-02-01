extends Node

var socket = WebSocketPeer.new()
var connected = false

func _ready():
	var token = "A_Z5Z4sUn33DJWfAr9v6dg"
	var room_id = "C715" # 來自 Discord 的房間代碼
	
	# 檢查是否在 Web 平台執行
	if OS.has_feature("web"):
		# 使用 JavaScriptBridge 讀取網址 URL 參數
		var window = JavaScriptBridge.get_interface("window")
		if window:
			var url_string = window.location.search
			# 建立 URLSearchParams 物件
			var url_params = JavaScriptBridge.create_object("URLSearchParams", url_string)
			if url_params.has("token"):
				token = url_params.get("token")
			if url_params.has("room"):
				room_id = url_params.get("room")
	
	# 建立連線 URL (符合 main.py 的 /ws/{room_id} 路由)
	var websocket_url = "ws://127.0.0.1:8080/ws/%s?token=%s" % [room_id, token]
	print("正在連線至伺服器: " + websocket_url)
	
	# 嘗試連線
	var err = socket.connect_to_url(websocket_url)
	if err != OK:
		print("無法連線至伺服器")
		set_process(false)

signal state_updated(state: GameModels.BattleState)

func _process(_delta):
	socket.poll()
	var state = socket.get_ready_state()
	
	if state == WebSocketPeer.STATE_OPEN:
		if not connected:
			connected = true
			print("連線到伺服器成功！")
			
		while socket.get_available_packet_count() > 0:
			var packet = socket.get_packet()
			print("收到封包，大小: ", packet.size()) # Debug
			
			var data_str = packet.get_string_from_utf8()
			print("封包內容: ", data_str) # Debug
			
			var json = JSON.new()
			var parse_result = json.parse(data_str)
			
			if parse_result == OK:
				var msg = json.data
				print("解析成功, Type: ", msg.get("type")) # Debug
				
				# 處理狀態更新
				if msg.get("type") == "STATE_UPDATE":
					# 從 Payload 解析 BattleState
					var payload = msg.get("payload")
					if payload:
						print("正在轉換 payload 至 BattleState...")
						var battle_state = GameModels.parse_state(payload)
						print("轉換完成，發送訊號！")
						state_updated.emit(battle_state)
					else:
						print("錯誤: Payload 是空的！")
			else:
				print("JSON 解析失敗: ", json.get_error_message())
				
	elif state == WebSocketPeer.STATE_CLOSING:
		pass
	elif state == WebSocketPeer.STATE_CLOSED:
		if connected:
			connected = false
			print("連線已中斷")
			# 這裡可以加入重連邏輯

func send_command(type: String, payload: Dictionary = {}):
	if socket.get_ready_state() != WebSocketPeer.STATE_OPEN:
		print("錯誤: 尚未連線，無法發送指令")
		return
		
	var msg = {
		"type": type,
		"payload": payload
	}
	socket.send_text(JSON.stringify(msg))
	print("已發送指令: ", type)
