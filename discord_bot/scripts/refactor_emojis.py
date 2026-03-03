
import json
import re
import os

BASE_DIR = "/home/terraria/servers/discord_bot"
DATA_DIR = os.path.join(BASE_DIR, "data/hihi")

def load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_json(path, data):
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def main():
    # 1. Load current files
    emojis_old = load_json(os.path.join(DATA_DIR, "emojis.json"))
    meanings_old = load_json(os.path.join(DATA_DIR, "emoji_meanings.json"))
    
    # 2. Parse official list from app_emojis.txt
    official_map = {} # ID -> Name
    official_code_map = {} # Name -> Code
    
    with open(os.path.join(BASE_DIR, "app_emojis.txt"), 'r', encoding='utf-8') as f:
        for line in f:
            # Line: App Emoji: name -> <a:name:id> ...
            match = re.search(r'App Emoji: (.+?) -> (<(?:a|):.+?:(\d+)>)', line)
            if match:
                name, code, eid = match.groups()
                official_map[eid] = name
                official_code_map[name] = code

    # 3. Build new clean dictionaries
    emojis_new = {}
    meanings_new = {}
    
    # Init emojis_new with ONLY official emojis
    for name, code in official_code_map.items():
        emojis_new[name] = code
        
    # 4. Migrate Meanings
    # Iterate through old meanings (aliases) and map them to official names
    for alias, description in meanings_old.items():
        # Find which ID this alias pointed to
        if alias in emojis_old:
            code = emojis_old[alias]
            # Extract ID from code
            match = re.search(r':(\d+)>', code)
            if match:
                eid = match.group(1)
                # Find official name for this ID
                if eid in official_map:
                    official_name = official_map[eid]
                    
                    # Add to meanings_new
                    if official_name in meanings_new:
                        # Conflict! Append if different
                        if description not in meanings_new[official_name]:
                            meanings_new[official_name] += f" / {description}"
                    else:
                        meanings_new[official_name] = description
                else:
                    print(f"⚠️ Alias '{alias}' has ID {eid} not found in official list.")
            else:
                 print(f"⚠️ Alias '{alias}' has invalid code format: {code}")
        else:
             print(f"⚠️ Meaning defined for '{alias}' but no code in emojis.json.")

    # 5. Save
    save_json(os.path.join(DATA_DIR, "emojis.json"), emojis_new)
    save_json(os.path.join(DATA_DIR, "emoji_meanings.json"), meanings_new)
    
    print(f"✅ Refactor complete.")
    print(f"Emojis count: {len(emojis_new)}")
    print(f"Meanings count: {len(meanings_new)}")

if __name__ == "__main__":
    main()
