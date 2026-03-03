import nbtlib
import struct
import io
import os

LEVEL_DAT_PATH = "/home/terraria/servers/minecraft/worlds/天寶伺服器/level.dat"

def verify_patch():
    if not os.path.exists(LEVEL_DAT_PATH):
        print(f"Error: {LEVEL_DAT_PATH} not found!")
        return

    try:
        with open(LEVEL_DAT_PATH, 'rb') as f:
            data = f.read()

        version = struct.unpack('<I', data[:4])[0]
        length = struct.unpack('<I', data[4:8])[0]
        nbt_data = data[8:]
        
        print(f"Header - Version: {version}, Length: {length}, Real Length: {len(nbt_data)}")

        class BedrockFile(nbtlib.File):
            byteorder = 'little'

        nbt_file = BedrockFile.parse(io.BytesIO(nbt_data))
        
        print("Keys in root:", list(nbt_file.keys()))
        
        if 'experiments' in nbt_file:
            print("Experiments tag FOUND!")
            print(nbt_file['experiments'])
        else:
            print("Experiments tag NOT found in root.")

    except Exception as e:
        print(f"Failed to read: {e}")

if __name__ == "__main__":
    verify_patch()
