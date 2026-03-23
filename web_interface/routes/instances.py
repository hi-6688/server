# routes/instances.py — 多實例管理路由
import json


def handle_list(handler, params, instance_manager):
    """GET /instances/list — 列出所有伺服器實例"""
    print("handle_list: start")
    insts = []
    print(f"handle_list: get_all_instances count={len(instance_manager.get_all_instances())}")
    for i in instance_manager.get_all_instances():
        print(f"handle_list: processing instance {i.name}")
        d = i.to_dict()
        print(f"handle_list: checking is_running for {i.name}")
        d['is_running'] = i.is_running()
        print(f"handle_list: done checking {i.name}")
        insts.append(d)
    print("handle_list: preparing headers")
    handler._set_headers()
    print("handle_list: writing response")
    handler.wfile.write(json.dumps({"instances": insts}).encode('utf-8'))
    print("handle_list: finish")


def handle_create(handler, params, instance_manager):
    """POST /instances/create — 建立新伺服器實例"""
    try:
        new_inst = instance_manager.create_instance(
            params.get('name'), params.get('port'), params.get('discord_channel_id', ''))
        handler._set_headers()
        handler.wfile.write(json.dumps({"status": "ok", "instance": new_inst.to_dict()}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_delete(handler, params, instance_manager):
    """POST /instances/delete — 刪除伺服器實例"""
    try:
        instance_manager.delete_instance(params.get('uuid'))
        handler._set_headers()
        handler.wfile.write(json.dumps({"status": "ok"}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))


def handle_update(handler, params, instance_manager):
    """POST /instances/update — 更新實例設定"""
    try:
        updated = instance_manager.update_instance(
            params.get('uuid'), params.get('name'), params.get('port'), params.get('discord_channel_id'))
        handler._set_headers()
        handler.wfile.write(json.dumps({"status": "ok", "instance": updated.to_dict()}).encode('utf-8'))
    except Exception as e:
        handler._set_headers(500)
        handler.wfile.write(json.dumps({"error": str(e)}).encode('utf-8'))
