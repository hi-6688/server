# level_utils.py — level.dat 讀取與同步工具
import os
import struct


def read_level_name(level_dat_path):
    """從 level.dat 二進位檔讀取世界名稱"""
    try:
        with open(level_dat_path, 'rb') as f:
            data = f.read()
        search_pattern = b'\x08\x09\x00LevelName'
        idx = data.find(search_pattern)
        if idx == -1:
            return None
        val_len_idx = idx + len(search_pattern)
        if val_len_idx + 2 > len(data):
            return None
        name_len = struct.unpack('<H', data[val_len_idx:val_len_idx + 2])[0]
        name_start = val_len_idx + 2
        if name_start + name_len > len(data):
            return None
        return data[name_start:name_start + name_len].decode('utf-8', errors='ignore')
    except:
        return None


def sync_cheats_enabled(instance):
    """同步 level.dat 的 cheatsEnabled 與 server.properties 的 allow-cheats"""
    try:
        # 讀取 server.properties 的 allow-cheats
        allow_cheats = False
        props_path = os.path.join(instance.path, 'server.properties')
        if os.path.exists(props_path):
            with open(props_path, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip().startswith('allow-cheats='):
                        allow_cheats = line.strip().split('=', 1)[1].lower() == 'true'
                        break

        # 讀取 level-name
        active_world = ''
        with open(props_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip().startswith('level-name='):
                    active_world = line.strip().split('=', 1)[1]
                    break
        if not active_world:
            return

        # 修改 level.dat
        dat_path = os.path.join(instance.path, 'worlds', active_world, 'level.dat')
        if not os.path.exists(dat_path):
            return

        with open(dat_path, 'rb') as f:
            data = bytearray(f.read())

        tag_name = b'cheatsEnabled'
        search = b'\x01' + struct.pack('<H', len(tag_name)) + tag_name
        idx = data.find(search)
        if idx == -1:
            return

        val_idx = idx + len(search)
        target_val = 1 if allow_cheats else 0
        if data[val_idx] != target_val:
            data[val_idx] = target_val
            with open(dat_path, 'wb') as f:
                f.write(data)
            print("Synced cheatsEnabled = %s for world '%s'" % (target_val, active_world))
    except Exception as e:
        print("Warning: Failed to sync cheatsEnabled: %s" % e)
