# pack_installer.py — 模組安裝與註冊工具
import os
import json
import re
import shutil


def install_single_pack(zf, filename, instance_path, forced_type=''):
    """從 zip 中讀取 manifest.json，判斷類型並安裝到正確目錄"""
    # 統一將反斜線轉為正斜線（Windows 建立的 zip 可能用反斜線）
    raw_names = zf.namelist()
    names = [n.replace('\\', '/') for n in raw_names]
    name_map = dict(zip(names, raw_names))

    # 找到 manifest.json
    manifest_path = None
    for n in names:
        if n.endswith('manifest.json') and n.count('/') <= 1:
            manifest_path = n
            break

    if not manifest_path:
        return None

    try:
        raw = zf.read(name_map[manifest_path])
        manifest = json.loads(raw.decode('utf-8-sig'))
    except:
        return None

    header = manifest.get('header', {})
    pack_uuid = header.get('uuid', '')
    pack_version = header.get('version', [1, 0, 0])
    pack_name = header.get('name', os.path.splitext(filename)[0])

    # 從 modules 判斷 pack 類型
    modules = manifest.get('modules', [])
    detected_type = 'behavior_packs'
    for mod in modules:
        mod_type = mod.get('type', '').lower()
        if mod_type in ('resources', 'resource'):
            detected_type = 'resource_packs'
            break
        elif mod_type in ('data', 'script', 'javascript'):
            detected_type = 'behavior_packs'
            break

    pack_type = forced_type if forced_type else detected_type

    # 安裝到對應目錄
    addon_dir = os.path.join(instance_path, pack_type)
    os.makedirs(addon_dir, exist_ok=True)

    safe_name = re.sub(r'[^\w\-.]', '_', pack_name) if re.search(r'[a-zA-Z]', pack_name) else pack_uuid
    target_dir = os.path.join(addon_dir, safe_name)
    if os.path.exists(target_dir):
        shutil.rmtree(target_dir)
    os.makedirs(target_dir, exist_ok=True)

    # 解壓縮檔案
    prefix = os.path.dirname(manifest_path)
    for name in names:
        if prefix and name.startswith(prefix):
            rel_path = name[len(prefix):].lstrip('/')
        else:
            rel_path = name
        if not rel_path or name.endswith('/'):
            continue
        target_path = os.path.join(target_dir, rel_path)
        os.makedirs(os.path.dirname(target_path), exist_ok=True)
        with open(target_path, 'wb') as out:
            out.write(zf.read(name_map[name]))

    print("Pack installed: %s (%s) -> %s/%s" % (pack_name, pack_uuid, pack_type, safe_name))
    return {
        'uuid': pack_uuid,
        'version': pack_version,
        'name': pack_name,
        'type': pack_type
    }


def register_packs_to_world(instance, packs):
    """將安裝的 pack 自動註冊到世界的 packs JSON"""
    # 讀取 level-name
    active_world = ''
    props_path = os.path.join(instance.path, 'server.properties')
    if os.path.exists(props_path):
        with open(props_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('level-name='):
                    active_world = line.strip().split('=', 1)[1]
                    break
    if not active_world:
        return

    world_path = os.path.join(instance.path, 'worlds', active_world)
    os.makedirs(world_path, exist_ok=True)

    for pack in packs:
        if pack['type'] == 'resource_packs':
            json_file = os.path.join(world_path, 'world_resource_packs.json')
        else:
            json_file = os.path.join(world_path, 'world_behavior_packs.json')

        existing = []
        if os.path.exists(json_file):
            try:
                with open(json_file, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except:
                existing = []

        already_exists = any(p.get('pack_id') == pack['uuid'] for p in existing)
        if not already_exists:
            existing.append({
                'pack_id': pack['uuid'],
                'version': pack['version']
            })
            with open(json_file, 'w', encoding='utf-8') as f:
                json.dump(existing, f, indent=2)
            print("Registered pack %s to %s" % (pack['name'], os.path.basename(json_file)))
