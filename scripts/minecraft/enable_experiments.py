#!/usr/bin/env python3
"""
Bedrock level.dat Experiments Modifier - Final Version
Inserts gametest tag into existing experiments compound
"""
import struct
import os
import sys

LEVEL_DAT_PATH = "/home/terraria/servers/minecraft/worlds/天寶伺服器/level.dat"
BACKUP_PATH = LEVEL_DAT_PATH + ".pre_experiment_bak"

def read_bedrock_level_dat(path):
    """Read Bedrock level.dat file with header"""
    with open(path, 'rb') as f:
        data = f.read()
    
    version = struct.unpack('<I', data[:4])[0]
    declared_length = struct.unpack('<I', data[4:8])[0]
    nbt_data = bytearray(data[8:])
    
    print(f"Header - Version: {version}, Declared Length: {declared_length}")
    
    return version, nbt_data

def insert_gametest_into_experiments(nbt_data):
    """
    Insert gametest byte tag into experiments compound
    
    Pattern to find: 0x0A 0x0B 0x00 'experiments'
    We need to insert AFTER the compound tag name, BEFORE any existing content
    
    Insert: 0x01 0x08 0x00 'gametest' 0x01
    """
    # Find experiments compound tag
    # Format: 0x0A (compound) + name_length(2,LE) + name
    search = b'\x0a\x0b\x00experiments'
    
    idx = nbt_data.find(search)
    if idx == -1:
        print("ERROR: 'experiments' compound tag not found")
        return nbt_data, False
    
    print(f"Found 'experiments' compound at position {idx}")
    
    # Check if gametest already exists
    gametest_search = b'\x01\x08\x00gametest'
    if gametest_search in nbt_data[idx:idx+100]:  # Check within experiments scope
        print("'gametest' tag already exists in experiments")
        # Try to find and modify it
        gt_idx = nbt_data.find(gametest_search, idx)
        if gt_idx != -1:
            value_pos = gt_idx + len(gametest_search)
            current = nbt_data[value_pos]
            if current == 0:
                nbt_data[value_pos] = 1
                print(f"Changed gametest from 0 to 1")
                return nbt_data, True
            else:
                print(f"gametest is already {current}")
                return nbt_data, False
    
    # Insert position: right after the experiments compound name
    insert_pos = idx + len(search)
    
    # Build gametest byte tag
    # 0x01 (byte type) + name_length(2) + name + value(1)
    gametest_tag = bytearray()
    gametest_tag.append(0x01)  # TAG_Byte
    gametest_tag.extend(b'\x08\x00')  # name length = 8 (LE)
    gametest_tag.extend(b'gametest')
    gametest_tag.append(0x01)  # value = 1 (enabled)
    
    # Insert
    nbt_data = nbt_data[:insert_pos] + gametest_tag + nbt_data[insert_pos:]
    
    print(f"Inserted gametest tag at position {insert_pos}")
    
    return nbt_data, True

def write_bedrock_level_dat(path, version, nbt_data):
    """Write Bedrock level.dat with updated header"""
    new_length = len(nbt_data)
    header = struct.pack('<II', version, new_length)
    
    with open(path, 'wb') as f:
        f.write(header + bytes(nbt_data))
    
    print(f"Written {path} - NBT Length: {new_length}")

def main():
    if not os.path.exists(LEVEL_DAT_PATH):
        print(f"ERROR: {LEVEL_DAT_PATH} not found")
        return 1
    
    # Backup
    if not os.path.exists(BACKUP_PATH):
        import shutil
        shutil.copy2(LEVEL_DAT_PATH, BACKUP_PATH)
        print(f"Backup created: {BACKUP_PATH}")
    
    # Read
    version, nbt_data = read_bedrock_level_dat(LEVEL_DAT_PATH)
    
    # Modify
    new_nbt_data, changed = insert_gametest_into_experiments(nbt_data)
    
    if not changed:
        print("No changes made")
        return 0
    
    # Write
    write_bedrock_level_dat(LEVEL_DAT_PATH, version, new_nbt_data)
    
    print("\n✅ SUCCESS: Beta APIs (gametest) enabled!")
    print("⚠️  IMPORTANT: Restart the Minecraft server now!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
