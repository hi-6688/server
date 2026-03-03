import asyncio
import os
import sys
from datetime import datetime
import dotenv

# Load environment variables
dotenv.load_dotenv(os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env'))

# Add current directory to path to import cogs
sys.path.append(os.path.dirname(__file__))

from cogs.ai_chat import AIChat

class MockUser:
    def __init__(self, name="User", id=123456789):
        self.name = name
        self.display_name = name
        self.id = id
        self.bot = False

class MockRole:
    def __init__(self, name, position=1, color=discord.Color.default()):
        self.name = name
        self.position = position
        self.color = color
        self.permissions = discord.Permissions.all()

class MockMember(MockUser):
    def __init__(self, name, id, roles=None):
        super().__init__(name, id)
        self.roles = roles or []
        self.nick = name
        self.guild_permissions = discord.Permissions.all()

class MockGuild:
    def __init__(self):
        self.name = "CLI_Server"
        self.me = MockMember("HiHi", 1468584012174987274, [MockRole("Bot"), MockRole("Admin")])
        self.members = [self.me]

    def get_member(self, user_id):
        return self.me if user_id == self.me.id else None

class MockChannel:
    def __init__(self, id=0):
        self.id = id
        self.guild = MockGuild()
        self.name = "cli-chat"
        
    async def send(self, content=None, embed=None, view=None):
        print(f"\n🤖 HiHi: {content}")
        if embed:
            print(f"[Embed] {embed.title}: {embed.description}")
        return MockMessage(content, self.id, MockUser("HiHi", 999))

    def typing(self):
        class TypingContext:
            async def __aenter__(self): pass
            async def __aexit__(self, exc_type, exc, tb): pass
        return TypingContext()

    async def fetch_message(self, id):
        return None

class MockMessage:
    def __init__(self, content, channel_id, author):
        self.content = content
        self.channel = MockChannel(channel_id)
        self.guild = self.channel.guild
        self.author = author
        self.created_at = datetime.now()
        self.attachments = []
        self.stickers = []
        self.mentions = []
        self.reference = None

class MockBot:
    def __init__(self):
        self.loop = asyncio.get_event_loop()
        self.user = MockUser("HiHi_CLI", 1468584012174987274) # Use actual bot ID
    
    def dispatch(self, event, *args, **kwargs):
        pass
        
    async def wait_until_ready(self):
        pass
        
    async def add_cog(self, cog):
        pass

async def main():
    print("🚀 Initializing HiHi CLI Mode...")
    
    # Initialize Bot and Cog
    bot = MockBot()
    ai_chat = AIChat(bot)
    
    # Wait for initialization (Client, Memory, etc.)
    # AIChat starts _init_ai task in __init__
    print("⏳ Waiting for AI initialization...")
    await asyncio.sleep(2) 
    
    if not ai_chat.client:
        print("❌ AI Client failed to initialize. Check GEMINI_API_KEY.")
        return

    # Override active channel IDs to allow CLI testing
    ai_chat.active_channel_ids = [0]
    
    print("\n✅ HiHi CLI Ready! (Type 'exit' to quit)")
    print("--------------------------------------------------")

    user = MockUser("ConsoleUser", 88888888)
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
        except EOFError:
            break
            
        if not user_input:
            continue
            
        if user_input.lower() in ('exit', 'quit'):
            break
            
        # Create Mock Message
        message = MockMessage(user_input, 0, user)
        
        # Manually trigger on_message logic
        # We invoke _process_buffer_task directly or simulate on_message?
        # Simulation is better to test full flow
        
        # Note: on_message is an async event listener. We call it directly.
        await ai_chat.on_message(message)
        
        # Wait a bit for async tasks to complete (since run_CLI is sync-blocking usually)
        # But here we are in async main, so we need to wait for the response task.
        # on_message creates a background task. We need to wait for it.
        
        # Simple spinner while waiting for response task
        for _ in range(200): # Wait up to 20s
            if ai_chat.response_task and not ai_chat.response_task.done():
                await asyncio.sleep(0.1)
            elif ai_chat.response_task and ai_chat.response_task.done():
                # Check for exceptions
                try:
                    ai_chat.response_task.result()
                except Exception as e:
                    print(f"❌ Error in task: {e}")
                break
            else:
                # No task started yet (maybe debounce?)
                await asyncio.sleep(0.1)

    print("👋 Bye!")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n👋 Bye!")
