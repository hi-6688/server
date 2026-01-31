import os

def hex_dump(path):
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return

    with open(path, 'rb') as f:
        data = f.read()
    
    # Search for "LevelName"
    term = b'LevelName'
    idx = data.find(term)
    
    if idx == -1:
        print("String 'LevelName' not found in file.")
        return

    print(f"Found 'LevelName' at index {idx}")
    
    # Show bytes before (Tag ID + Name Length)
    start = max(0, idx - 3)
    end = min(len(data), idx + len(term) + 20) # Show payload too
    
    chunk = data[start:end]
    print(f"Hex context: {chunk.hex(' ')}")
    print(f"ASCII context: {chunk}")
    
    # Check strict pattern
    pattern = b'\x08\x09\x00LevelName'
    strict_idx = data.find(pattern)
    print(f"Strict pattern found: {strict_idx != -1}")

worlds_dir = '/home/terraria/servers/minecraft/worlds'
for d in os.listdir(worlds_dir):
    p = os.path.join(worlds_dir, d, 'level.dat')
    if os.path.exists(p):
        print(f"--- Checking {d} ---")
        hex_dump(p)
