
import discord
import os
import json
import asyncio
from dotenv import load_dotenv

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENV_FILE = os.path.join(os.path.dirname(BASE_DIR), ".env")
EMOJI_FILE = os.path.join(os.path.dirname(BASE_DIR), "discord_bot/data/hihi/emojis.json")

load_dotenv(ENV_FILE)
TOKEN = os.getenv("DISCORD_TOKEN")

class EmojiVerifier(discord.Client):
    async def on_ready(self):
        print(f"Logged in as {self.user}")
        
        try:
            # 1. Load Local
            with open(EMOJI_FILE, 'r') as f:
                local_emojis = json.load(f)
            print(f"Loaded {len(local_emojis)} local emojis.")

            # 2. Fetch Remote
            app = await self.application_info()
            print(f"Fetching Remote Emojis for App ID: {app.id}...")
            
            data = await self.http.request(
                discord.http.Route('GET', f'/applications/{app.id}/emojis')
            )
            
            remote_map = {e['name']: e for e in data['items']}
            print(f"Found {len(remote_map)} remote emojis.")
            
            # 3. Compare
            new_config = {}
            fixed_count = 0
            
            # Use remote as source of truth for IDs and Animation
            for name, r_emoji in remote_map.items():
                r_id = r_emoji['id']
                r_anim = r_emoji.get('animated', False)
                anim_str = "a" if r_anim else ""
                
                # Construct correct code
                correct_code = f"<{anim_str}:{name}:{r_id}>"
                
                # Check if local matches
                if name in local_emojis:
                    if local_emojis[name] != correct_code:
                        print(f"⚠️ Mismatch for '{name}':")
                        print(f"  Local:  {local_emojis[name]}")
                        print(f"  Remote: {correct_code}")
                        fixed_count += 1
                else:
                    print(f"➕ New remote emoji found: {name}")
                    fixed_count += 1
                
                new_config[name] = correct_code
            
            # Check for local keys that don't exist remotely
            for l_name in local_emojis:
                if l_name not in remote_map:
                    print(f"❌ Local emoji not found in remote: '{l_name}' (will be removed)")
                    fixed_count += 1

            # 4. Save if needed
            if fixed_count > 0:
                print(f"\nFixing {fixed_count} issues...")
                with open(EMOJI_FILE, 'w', encoding='utf-8') as f:
                    json.dump(new_config, f, ensure_ascii=False, indent=2)
                print("✅ emojis.json updated!")
            else:
                print("\n✅ All emojis match perfectly!")

        except Exception as e:
            print(f"❌ Error: {e}")
            
        await self.close()

if __name__ == "__main__":
    intents = discord.Intents.default()
    client = EmojiVerifier(intents=intents)
    client.run(TOKEN)
