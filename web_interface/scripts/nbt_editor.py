import struct
import os
import sys

def modify_level_dat(file_path, new_name):
    """
    Modifies the LevelName in a Bedrock level.dat file.
    Bedrock level.dat format:
    - Version (4 bytes, usually < 10)
    - Data Length (4 bytes, LE)
    - NBT Data
    """
    if not os.path.exists(file_path):
        return False, "File not found"

    with open(file_path, 'rb') as f:
        data = bytearray(f.read())

    # Basic Header Check
    if len(data) < 8:
        return False, "File too short"
    
    version = struct.unpack('<I', data[0:4])[0]
    nbt_len = struct.unpack('<I', data[4:8])[0]
    
    # Verify NBT length (it should match file_size - 8, or be close)
    # Note: Sometimes there is extra padding or garbage? Usually accurate.
    
    # Search for LevelName tag
    # Tag String (8) + Name Length (2 bytes LE: 09 00) + "LevelName"
    search_pattern = b'\x08\x09\x00LevelName'
    idx = data.find(search_pattern)
    
    if idx == -1:
        return False, "LevelName tag not found"
    
    # Position of Value Length (Short)
    # Pattern starts at idx. Length is len(pattern) = 1 + 2 + 9 = 12
    # So Value Length is at idx + 12
    val_len_idx = idx + 12
    
    if val_len_idx + 2 > len(data):
        return False, "Files structure error"
        
    current_name_len = struct.unpack('<H', data[val_len_idx:val_len_idx+2])[0]
    current_name_end = val_len_idx + 2 + current_name_len
    
    # Old Name for logging
    # old_name = data[val_len_idx+2 : current_name_end].decode('utf-8', errors='ignore')
    
    # Encode new name
    new_name_bytes = new_name.encode('utf-8')
    new_name_len = len(new_name_bytes)
    
    # Construct new data
    # 1. Header (0-8) -> Update Length
    # 2. Pre-Tag Data (8 - val_len_idx)
    # 3. New Length (2 bytes)
    # 4. New Name
    # 5. Post-Data (current_name_end - End)
    
    # Calculate size difference
    diff = new_name_len - current_name_len
    new_nbt_len = nbt_len + diff
    
    # Update Header
    struct.pack_into('<I', data, 4, new_nbt_len)
    
    # Construction
    new_data = data[:val_len_idx]
    new_data += struct.pack('<H', new_name_len)
    new_data += new_name_bytes
    new_data += data[current_name_end:]
    
    with open(file_path, 'wb') as f:
        f.write(new_data)
        
    return True, f"Renamed to {new_name}"

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python3 nbt_editor.py <path> <new_name>")
        sys.exit(1)
        
    path = sys.argv[1]
    name = sys.argv[2]
    
    success, msg = modify_level_dat(path, name)
    if success:
        print(f"SUCCESS: {msg}")
    else:
        print(f"ERROR: {msg}")
        sys.exit(1)
