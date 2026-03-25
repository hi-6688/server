import nbtlib
import shutil
import os
import io
import struct

LEVEL_DAT_PATH = "/home/terraria/servers/minecraft/worlds/天寶伺服器/level.dat"
BACKUP_PATH = f"{LEVEL_DAT_PATH}.bak"

def patch_level_dat():
    if not os.path.exists(LEVEL_DAT_PATH):
        print(f"Error: {LEVEL_DAT_PATH} not found!")
        return

    # Backup first
    if not os.path.exists(BACKUP_PATH):
        print(f"Backing up level.dat to {BACKUP_PATH}...")
        shutil.copy2(LEVEL_DAT_PATH, BACKUP_PATH)

    try:
        with open(LEVEL_DAT_PATH, 'rb') as f:
            data = f.read()

        # Parse Bedrock Header
        # Version (4 bytes LE) + Length (4 bytes LE)
        version = struct.unpack('<I', data[:4])[0]
        length = struct.unpack('<I', data[4:8])[0]
        nbt_data = data[8:]
        
        print(f"Bedrock Header - Version: {version}, Length: {length}")
        
        # Verify length matches remaining data? (Usually it does, or implies content length)
        # Verify file size
        # nbt_data size should be close to length.
        
        # Configure nbtlib for Little Endian
        # nbtlib uses a context manager or global config for byteorder?
        # Actually nbtlib 1.x/2.x differs. Let's try parsing with explicit byteorder context if possible,
        # or just assume nbtlib might auto-detect? No, default is Big Endian.
        
        # We need to use `nbtlib.File.parse` but wrap it in byteorder config
        

        # Inspecting nbtlib source (implied):
        # File class usually has byteorder attribute.
        
        class BedrockFile(nbtlib.File):
            byteorder = 'little'
            
        if nbt_data[0] != 0x0A:
             print(f"Error: Start byte is {hex(nbt_data[0])}, expected 0x0A")
             return

        # Parse using BedrockFile
        nbt_file = BedrockFile.parse(io.BytesIO(nbt_data))
        print("Parsed Bedrock NBT successfully!")
        
        if 'experiments' not in nbt_file:
             print("Creating 'experiments' tag...")
             nbt_file['experiments'] = nbtlib.Compound({})
             
        experiments = nbt_file['experiments']
        experiments['gametest'] = nbtlib.Byte(1)
        experiments['experiments_ever_used'] = nbtlib.Byte(1)
        experiments['saved_with_toggled_experiments'] = nbtlib.Byte(1)
        
        print("Enabled 'gametest' experiment.")
        
        # Serialize back
        buffer = io.BytesIO()
        nbt_file.write(buffer) # Should use class byteorder
        new_nbt_data = buffer.getvalue()

            
            # Reconstruct header with NEW length
        # Reconstruct header with NEW length
        new_length = len(new_nbt_data)
        new_header = struct.pack('<II', version, new_length)
        
        with open(LEVEL_DAT_PATH, 'wb') as f:
            f.write(new_header + new_nbt_data)
            
        print(f"Patched {LEVEL_DAT_PATH} successfully! (New Size: {len(new_header) + len(new_nbt_data)})")

    except Exception as e:
        print(f"Failed to patch: {e}")
        import traceback
        traceback.print_exc()
        # Restore backup
        if os.path.exists(BACKUP_PATH):
            shutil.copy2(BACKUP_PATH, LEVEL_DAT_PATH)
            print("Restored backup due to error.")

if __name__ == "__main__":
    patch_level_dat()
