import sys
sys.path.append("/home/terraria/servers/discord_bot")
try:
    import cogs.ai_chat
    print("Syntax OK")
except Exception as e:
    print(f"Error: {e}")
