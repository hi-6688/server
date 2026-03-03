
import json
import os
import re

DATA_DIR = "/home/terraria/servers/discord_bot/data/hihi"
EMOJI_FILE = os.path.join(DATA_DIR, "emojis.json")
MEANINGS_FILE = os.path.join(DATA_DIR, "emoji_meanings.json")
APP_EMOJIS_FILE = "/home/terraria/servers/discord_bot/app_emojis.txt"

# [Simplify Mapping]
# Old -> New
RENAME_MAP = {
    "crowbar_Draw": "crowbar",
    "crowbar_Draw2": "crowbar2",
    "UI_Bubble_Chat": "loading",
    "UI_Bubble_Chat2": "loading2",
    "ReadytoEat": "ready",
    "Exclamationmark": "alert",
    "Giveflowers": "flower",
    "watchtosleep": "sleep_watch",
    "angrywatching": "angry_watch",
    "angrytyping": "angry_type",
    "Sweat_Awkward": "awkward",
    "questionmark": "question",
    "knife_Draw": "knife",
    "lickscreen": "lick",
    "cheer2": "cheer_glow",
}

def update_file(file_path, type="json"):
    print(f"Processing {file_path}...")
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return

    if type == "json":
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        new_data = {}
        changed = False
        
        for k, v in data.items():
            new_key = RENAME_MAP.get(k, k)
            new_data[new_key] = v
            if new_key != k:
                print(f"  Renamed: {k} -> {new_key}")
                changed = True
        
        if changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(new_data, f, ensure_ascii=False, indent=2)
            print("  Saved.")
            
    elif type == "txt":
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        new_lines = []
        changed = False
        for line in lines:
            line = line.strip()
            if not line: continue
            
            # Format: name: <code:id>
            parts = line.split(":", 1)
            if len(parts) >= 2:
                name = parts[0].strip()
                rest = parts[1]
                new_name = RENAME_MAP.get(name, name)
                new_lines.append(f"{new_name}: {rest}\n")
                if new_name != name:
                    changed = True
            else:
                new_lines.append(line + "\n")
        
        if changed:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.writelines(new_lines)
            print("  Saved.")

if __name__ == "__main__":
    update_file(EMOJI_FILE, "json")
    update_file(MEANINGS_FILE, "json")
    update_file(APP_EMOJIS_FILE, "txt")
    print("Done.")
